import os
from dotenv import load_dotenv

load_dotenv(override=True)
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
AWS_REGION = os.getenv('AWS_REGION')

EMAIL_USER = os.getenv('EMAIL_USER') 
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD') 
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = os.getenv('SMTP_PORT')
SECRET_KEY = os.getenv('JWT_SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')

MONGO_CLIENT = os.getenv('MONGO_CLIENT_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
SUPER_ADMIN_USERS = os.getenv('ADMIN_USERS')
BACKEND_URL = os.getenv('BACKEND_URL')