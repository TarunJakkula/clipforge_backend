from middleware.middleware import create_access_token
from email_validator import EmailNotValidError
from email.mime.multipart import MIMEMultipart
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pydantic import validate_email
from models.pydantic_models import *
from utils.mongodb_schemas import *
from utils.env_variables import *
import smtplib, pyotp, uuid
import hashlib

router = APIRouter()

with open('api/auth/prompts/stage_1_prompt.txt', 'r') as f:
    static_stage_1_prompt = f.read()
with open('api/auth/prompts/stage_2_prompt.txt', 'r') as f:
    static_stage_2_prompt = f.read()
with open('api/auth/prompts/broll_prompt.txt', 'r') as f:
    broll_prompt = f.read()
with open('api/auth/prompts/music_prompt.txt', 'r') as f:
    music_prompt = f.read()

def send_email(to_email: str, otp: str):
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)

            with open('template/otp-verification-email-template.html', 'r') as file:
                html_content = file.read()
            html_content = html_content.replace('{Insert OTP}', otp)

            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'OTP Verification'
            msg['From'] = EMAIL_USER
            msg['To'] = to_email
            msg.attach(MIMEText(html_content, 'html'))
            server.sendmail(EMAIL_USER, to_email, msg.as_string())

    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to send email: {str(e)}')

@router.post('/user_login/', tags=['User'])
async def user_login(request: UserLoginRequest):
    try:
        validate_email(request.email)
    except EmailNotValidError:
        raise HTTPException(status_code=401, detail='Invalid email address')

    totp = pyotp.TOTP(pyotp.random_base32(), interval=300)  # 5 minutes expiry
    otp = totp.now()

    otp_id = str(uuid.uuid4())
    otp_data = {
        'otp_id': otp_id,
        'email': request.email,
        'otp_hash': hashlib.sha256(otp.encode()).hexdigest(),
        'expiry_time': datetime.utcnow() + timedelta(seconds=300)
    }
    otp_collection.insert_one(otp_data)
    try:
        send_email(request.email, otp)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f'Unable to send OTP: {str(e)}')

    return {'otp_id': otp_id}

@router.post('/verify_user/', tags=['User'])
async def verify_user(request: OTPVerifyRequest):
    otp_info = otp_collection.find_one({'otp_id': request.otp_id})
    if not otp_info:
        raise HTTPException(status_code=404, detail='No OTP found for this email')

    stored_hash = otp_info.get('otp_hash')
    otp_expiry = otp_info.get('expiry_time')

    if datetime.utcnow() > otp_expiry:
        otp_collection.delete_one({'otp_id': request.otp_id})
        raise HTTPException(status_code=401, detail='OTP has expired')

    entered_hash = hashlib.sha256(request.otp.encode()).hexdigest()
    if stored_hash != entered_hash:
        raise HTTPException(status_code=401, detail='Invalid OTP')
    otp_collection.delete_one({'otp_id': request.otp_id})
    existing_user = users_collection.find_one({'email': otp_info['email']})
    if not existing_user:
        user_id = str(uuid.uuid4())
        user_data = {
            'user_id': user_id,
            'email': otp_info['email'],
            'username': otp_info['email'].split('@')[0],
        }
        users_collection.insert_one(user_data)
        space_id = str(uuid.uuid4())
        default_space = {
            'space_id': space_id,
            'colour_code': '#0F00E5',
            'name': otp_info['email'].split('@')[0],
            'user_id': user_id
        }
        spaces_collection.insert_one(default_space)
        prompt_data = {
            'stage_1_prompt': static_stage_1_prompt.lstrip().rstrip(),
            'stage_2_prompt': static_stage_2_prompt.lstrip().rstrip(),
            'broll_prompt': broll_prompt.lstrip().rstrip(),
            'music_prompt': music_prompt.lstrip().rstrip(),
            'versions': {
                '1': [{'id':str(uuid.uuid4()), 'name': 'Untitled', 'prompt': static_stage_1_prompt, 'active': True}],
                '2': [{'id': str(uuid.uuid4()), 'name': 'Untitled', 'prompt': static_stage_2_prompt, 'active': True}],
                '3': [{'id': str(uuid.uuid4()), 'name': 'Untitled', 'prompt': broll_prompt, 'active': True}],
                '4': [{'id': str(uuid.uuid4()), 'name': 'Untitled', 'prompt': music_prompt, 'active': True}]
            },
            'space_id': space_id
        }
        prompts_collection.insert_one(prompt_data)
    else:
        user_id = existing_user['user_id']

    access_token_expires = timedelta(minutes=1440)
    access_token = create_access_token(
        data={'sub': otp_info['email']},
        expires_delta=access_token_expires
    )
    return {'user_id': user_id, 'email': otp_info['email'], 'access_token': access_token}