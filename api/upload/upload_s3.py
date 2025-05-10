from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from utils.env_variables import AWS_REGION, S3_BUCKET_NAME
from models.pydantic_models import CompleteUploadRequest
from botocore.exceptions import ClientError
from utils.mongodb_schemas import *
from utils.s3_session import s3
from typing import Any
import hashlib
import uuid
router = APIRouter()

@router.post('/initiate_upload/', tags=['Upload'])
async def initiate_upload(file_name: str = Form(...), category: str = Form(...)) -> Any:
    try:
        unique_string = f'{file_name}-{uuid.uuid4()}'
        file_id = hashlib.sha256(unique_string.encode()).hexdigest()
        file_extension = file_name.split('.')[-1]
        file_key = f'{category}/{file_id}.{file_extension}'
        params = {
            'Bucket': S3_BUCKET_NAME,
            'Key': file_key,
            'ContentType': f'video/{file_extension}',
        }

        upload = s3.create_multipart_upload(**params)
        return {'uploadId': upload['UploadId'], 'fileId': file_id}

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f'Error initializing upload: {str(e)}')

@router.post('/upload_chunks/', tags=['Upload'])
async def upload_chunk(
    file: UploadFile = File(...),
    part_number: int = Form(...),
    upload_id: str = Form(...),
    file_name: str = Form(...),
    file_id: str = Form(...),
    category: str = Form(...)
):
    try:
        file_content = await file.read()
        file_extension = file_name.split('.')[-1]
        file_key = f'{category}/{file_id}.{file_extension}'
        s3_params = {
            'Bucket': S3_BUCKET_NAME,
            'Key': file_key,
            'Body': file_content,
            'PartNumber': part_number,
            'UploadId': upload_id,
        }
        response = s3.upload_part(**s3_params)
        return {'success': True, 'message': 'Chunk uploaded successfully', 'ETag': response['ETag']}

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f'Error uploading chunk: {str(e)}')

@router.post('/complete_upload/', tags=['Upload'])
async def complete_upload(request: CompleteUploadRequest) -> Any:
    try:
        file_extension = request.file_name.split('.')[-1]
        file_key = f'{request.category}/{request.file_id}.{file_extension}'
        s3_params = {
            'Bucket': S3_BUCKET_NAME,
            'Key': file_key,
            'UploadId': request.upload_id
        }
        parts_list = s3.list_parts(**s3_params)
        parts = []
        for part in parts_list['Parts']:
            parts.append({'ETag': part['ETag'], 'PartNumber': part['PartNumber']})

        s3_params['MultipartUpload'] = {'Parts': parts}
        s3.complete_multipart_upload(**s3_params)
        file_storage_link = f'https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_key}'
        existing_user = users_collection.find_one({'user_id': request.user_id})
        if not existing_user :
            raise HTTPException(status_code=500, detail='User not found')
        file_id = str(uuid.uuid4())
        if request.category=='clips':
            clip_data = {
                'clip_id': file_id,
                'clip_name': request.file_name,
                'clip_storage_link' : file_storage_link,
                'clip_transcript' : None,
                'clip_duration': None,
                'aspect_ratio': request.aspect_ratio,
                'space_id': request.space_id,
                'subclips': False
            }
            clips_collection.insert_one(clip_data)
        elif request.category=='broll':
            if request.parent_id == 'root':
                spaces = [request.space_id]
            else:
                folder_info = folders_collection.find_one({'folder_id': request.parent_id})
                spaces = list(set(folder_info['spaces'] + [request.space_id]))
            file_data = {
                'file_id': file_id,
                'file_name': request.file_name,
                'file_storage_link' : file_storage_link,
                'tags': request.tags,
                'parent_id': request.parent_id,
                'space_id': request.space_id,
                'spaces': spaces,
                'aspect_ratio': request.aspect_ratio
            }
            brolls_collection.insert_one(file_data)
            for tag in request.tags:
                if not tags_collection.find_one({'file_id': file_id, 'space_id': request.space_id, 'tag_name': tag.lower()}) :
                    tag_info = {
                        'tag_name': tag.lower(),
                        'file_id': file_id,
                        'space_id': request.space_id,
                        'category': 'broll'
                    }
                    tags_collection.insert_one(tag_info)
        elif request.category=='music':
            if request.parent_id == 'root':
                spaces = [request.space_id]
            else :
                folder_info = folders_collection.find_one({'folder_id': request.parent_id})
                spaces = list(set(folder_info['spaces'] + [request.space_id]))
            file_data = {
                'file_id': file_id,
                'file_name': request.file_name,
                'file_storage_link' : file_storage_link,
                'tags': request.tags,
                'parent_id': request.parent_id,
                'space_id': request.space_id,
                'spaces': spaces
            }
            music_collection.insert_one(file_data)
            for tag in request.tags:
                if not tags_collection.find_one({'file_id': file_id, 'space_id': request.space_id, 'tag_name': tag.lower()}) :
                    tag_info = {
                        'tag_name': tag.lower(),
                        'file_id': file_id,
                        'space_id': request.space_id,
                        'category': 'music'
                    }
                    tags_collection.insert_one(tag_info)
        return {'clip_id': file_id, 'location': file_storage_link}

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f'Error completing upload: {str(e)}')