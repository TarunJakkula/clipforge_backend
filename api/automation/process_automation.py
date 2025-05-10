from models.pydantic_models import AutomateProcess, AutomationRestart
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from api.transcript.whisper_model import process_generate_transcript
from api.stage_three.stage_three_api import add_broll_music_presets
from api.stage_two.stage_two_api import remix_transcripts
from api.stage_one.stage_one_api import process_clips
from email.mime.multipart import MIMEMultipart
from socket_server import socket_server
from email.mime.text import MIMEText
import uuid, asyncio, smtplib, time
from utils.log_errors import logger
from utils.mongodb_schemas import *
from utils.env_variables import *
from bson import json_util
import json

process_success_template_path = 'template/process-completion.html'
process_failure_template_path = 'template/process-failed.html'
router = APIRouter()

async def update_task_status(task_id: str, stage: str, status: int):
    try:
        await asyncio.to_thread(tasks_collection.update_one, {'task_id': task_id}, {'$set': {f'flags.{stage}': status}})
        task_info = await asyncio.to_thread(tasks_collection.find_one, {'task_id': task_id})
        if not task_info:
            return

        formatted_data = {
            'task_id': task_id,
            'title': task_info.get('title', 'Untitled'),
            'flags': task_info.get('flags', {})
        }
        await socket_server.emit('task_updated', formatted_data)
    except Exception as e:
        logger.error(f"Error updating task status: {e}")

async def send_email_async(to_email: str, template_path: str, stage: str):
    try:
        await asyncio.to_thread(send_email, to_email, template_path, stage)
        logger.info(f"Email sent successfully for {stage}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def send_email(to_email: str, template_path: str, stage: str):
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)

            with open(template_path, 'r') as file:
                html_content = file.read().replace('{STAGE}', stage)

            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'ClipForge Project Status'
            msg['From'] = EMAIL_USER
            msg['To'] = to_email
            msg.attach(MIMEText(html_content, 'html'))
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
    except Exception as e:
        raise Exception(f'Email sending failed: {e}')

async def automation(space_id: str, clip_id: str, task_id: str):
    try:
        clip_info = await asyncio.to_thread(clips_collection.find_one, {'clip_id': clip_id})
        if not clip_info:
            logger.error("Clip not found")
            await update_task_status(task_id, 'status', -1)
            return

        # Transcription
        try:
            if clip_info.get('clip_transcript') and clip_info['clip_transcript'].get('transcript_text'):
                await update_task_status(task_id, 'transcribed', 1)
            else :
                logger.info("Starting transcription")
                await asyncio.to_thread(process_generate_transcript, clip_id)
                updated_clip_info = await asyncio.to_thread(clips_collection.find_one, {'clip_id': clip_id})
                if not updated_clip_info['clip_transcript'].get('transcript_text'):
                    raise ValueError("Transcript not found after processing")
                await update_task_status(task_id, 'transcribed', 1)
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            await update_task_status(task_id, 'transcribed', -1)
            return

        # Stage 1
        try:
            updated_clip_info = await asyncio.to_thread(clips_collection.find_one, {'clip_id': clip_id})
            if updated_clip_info['subclips'] :
                await update_task_status(task_id, 'stage1', 1)
            else :
                logger.info("Starting Stage 1")
                await asyncio.to_thread(process_clips, space_id, updated_clip_info)
                await asyncio.to_thread(clips_collection.update_one, {'clip_id': clip_id}, {'$set': {'subclips': True}})
                await update_task_status(task_id, 'stage1', 1)
        except Exception as e:
            logger.error(f"Stage 1 failed: {e}")
            await update_task_status(task_id, 'stage1', -1)
            return

        # Stage 2
        try:
            logger.info("Starting Stage 2")
            updated_clip_info = await asyncio.to_thread(clips_collection.find_one, {'clip_id': clip_id})
            await asyncio.to_thread(remix_transcripts, space_id, updated_clip_info)
            await update_task_status(task_id, 'stage2', 1)
        except Exception as e:
            logger.error(f"Stage 2 failed: {e}")
            await update_task_status(task_id, 'stage2', -1)
            return

        # Stage 3
        try:
            logger.info("Starting Stage 3")
            subclips = await asyncio.to_thread(lambda: list(subclips_collection.find({'clip_id': clip_id})))
            if not subclips:
                raise ValueError("No subclips found for Stage 3")
            for subclip in subclips:
                await asyncio.to_thread(add_broll_music_presets, space_id, subclip['subclip_id'])
            await update_task_status(task_id, 'stage3', 1)
        except Exception as e:
            logger.error(f"Stage 3 failed: {e}")
            await update_task_status(task_id, 'stage3', -1)
            return

        logger.info("Process completed successfully")
        space_info = await asyncio.to_thread(spaces_collection.find_one, {'space_id': space_id})
        user_info = await asyncio.to_thread(users_collection.find_one, {'user_id': space_info['user_id']})
        await send_email_async(user_info.get('email'), process_success_template_path, 'Process Completed')
    except Exception as e:
        try:
            space_info = await asyncio.to_thread(spaces_collection.find_one, {'space_id': space_id})
            user_info = await asyncio.to_thread(users_collection.find_one, {'user_id': space_info['user_id']})
            await send_email_async(user_info.get('email'), process_failure_template_path, 'Process Failed')
            logger.info('Process failed, email sent to user.')
        except Exception as email_error:
            logger.error(f"Failed to send failure email: {email_error}")

@router.post('/automate_process/', tags=['Automation'])
async def automate_process(request: AutomateProcess, backgroundtasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    clip_info = clips_collection.find_one({'clip_id': request.clip_id, 'space_id': request.space_id})
    if not clip_info:
        raise HTTPException(status_code=404, detail=f'Clip not found')
    try:
        task = {
            'task_id': task_id,
            'title': clip_info['clip_name'],
            'flags': {
                'uploaded': 1,
                'transcribed': 0,
                'stage1': 0,
                'stage2': 0,
                'stage3': 0
            }
        }
        task_info = {
            **task,
            'clip_id': request.clip_id,
            'space_id': request.space_id
        }
        tasks_collection.insert_one(task_info)
        backgroundtasks.add_task(automation, request.space_id, request.clip_id, task_id)
        await socket_server.emit('task_added', {'space_id': request.space_id, 'task': task})
        return {'message': 'Process started.', 'task_id': task_id}
    
    except Exception as e:
        try:
            tasks_collection.delete_one({'task_id': task_id})
        except:
            pass
        raise HTTPException(status_code=500, detail=f'Process initiation failed: {str(e)}')

@router.post('/task_restart/', tags=['Automation'])
async def task_restart(request: AutomationRestart, backgroundtasks: BackgroundTasks):
    try:
        task_exists = tasks_collection.find_one({'task_id': request.task_id})
        if not task_exists:
            await socket_server.emit('task_deleted', request.task_id)
            return {'message': 'Task does not exist'}
        
        flags = {
            'uploaded': 1,
            'transcribed': 0,
            'stage1': 0,
            'stage2': 0,
            'stage3': 0
        }
        tasks_collection.update_one(
            {'task_id': request.task_id},
            {'$set': {'flags': flags}}
        )
        formatted_data = {
            'task_id': request.task_id,
            'title': task_exists.get('title', 'Untitled'),
            'flags': flags
        }
        await socket_server.emit('task_updated', formatted_data)
        backgroundtasks.add_task(automation, task_exists['space_id'], task_exists['clip_id'], request.task_id)
        return {'message': 'Task restarted.'}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error while restarting the automation: {str(e)}')
    
@router.get('/fetch_tasks/', tags=['Automation'])
async def fetch_tasks(space_id: str = Query(...)):
    try:
        tasks_list = list(tasks_collection.find({'space_id': space_id}))  
        json_tasks = json.loads(json_util.dumps(tasks_list))
        return {'tasks': json_tasks}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Error fetching tasks: {str(e)}')
    
@router.delete('/task_abort/', tags=['Automation'])
async def task_abort(task_id: str = Query(...)):
    try:
        task_exists = tasks_collection.find_one({'task_id': task_id})
        if not task_exists:
            await socket_server.emit('task_deleted', task_id)
            return {'message': 'Task does not exist'}
        
        tasks_collection.delete_one({'task_id': task_id})
        await socket_server.emit('task_deleted', task_id)
        return {'message': 'Task deleted successfully.'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Error aborting the process: {str(e)}')