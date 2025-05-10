from utils.mongodb_schemas import clips_collection, subclips_collection, remixed_clips_collection
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from utils.env_variables import S3_BUCKET_NAME
from utils.log_errors import logger
import boto3

router = APIRouter()
s3 = boto3.resource('s3')

def delete_remixed_clips(files: list):
    for file in files:
        try:
            file_key = '/'.join(file['remixed_clip_link'].split('/')[-2:])
            s3.Object(S3_BUCKET_NAME, file_key).delete()
            remixed_clips_collection.delete_one({'remixed_clip_id': file['remixed_clip_id']})
        except Exception as e:
            logger.error(f"Error deleting file {file['remixed_clip_link']}: {e}")
            continue

def delete_subclips(files: list):
    for file in files:
        try:
            file_key = '/'.join(file['subclip_storage_link'].split('/')[-2:])
            s3.Object(S3_BUCKET_NAME, file_key).delete()
            subclips_collection.delete_one({'subclip_id': file['subclip_id']})
            if file['remixes']:
                remixes_exists = list(remixed_clips_collection.find({'subclip_id': file['subclip_id']}))
                delete_remixed_clips(remixes_exists)
        except Exception as e:
            logger.error(f"Error deleting file {file['subclip_storage_link']}: {e}")
            continue
            
def delete_clip(files: list):
    for file in files:
        try:
            file_key = '/'.join(file['clip_storage_link'].split('/')[-2:])
            s3.Object(S3_BUCKET_NAME, file_key).delete()
            clips_collection.delete_one({'clip_id': file['clip_id']})
            if file['subclips']: 
                subclips_exists = list(subclips_collection.find({'clip_id': file['clip_id']}))
                delete_subclips(subclips_exists)
        except Exception as e:
            logger.error(f"Error deleting file {file['clip_storage_link']}: {e}")
            continue

@router.delete('/delete_video/', tags=['Delete'])
async def delete_video(id: str = Query(...), category: str = Query(...), backgroundtasks: BackgroundTasks = BackgroundTasks(None)):
    if category=='clip':
        clip_data = clips_collection.find_one({'clip_id': id})
        if not clip_data:
            raise HTTPException(status_code=404, detail='Clip not found')
        backgroundtasks.add_task(delete_clip, [clip_data])
    elif category=='subclip':
        subclip_data = subclips_collection.find_one({'subclip_id': id})
        if not subclip_data:
            raise HTTPException(status_code=404, detail='Subclip not found')
        backgroundtasks.add_task(delete_subclips, [subclip_data])
    elif category=='remixclip':
        remixed_data = remixed_clips_collection.find_one({'remixed_clip_id': id})
        if not remixed_data:
            raise HTTPException(status_code=404, detail='Remixed clip not found')
        backgroundtasks.add_task(delete_remixed_clips, [remixed_data])
        
    return {'message': 'Deletion process started.'}