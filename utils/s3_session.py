from utils.env_variables import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, S3_BUCKET_NAME
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException
import boto3

session = boto3.Session(
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)
s3 = session.client('s3')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

def upload_to_s3(file_path, s3_key):
    try:
        s3.upload_file(file_path, S3_BUCKET_NAME, s3_key)
        s3_url = f'https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}'
        return s3_url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to upload file to S3: {str(e)}')

s3_download = boto3.client('s3')
def download_from_s3(link, local_path):
    try:
        s3_key = '/'.join(link.split('/')[-2:])
        s3_download.download_file(S3_BUCKET_NAME, s3_key, local_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file from S3: {str(e)}")