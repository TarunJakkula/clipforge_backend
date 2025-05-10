from models.pydantic_models import UpdatePrompt, EditPromptName, AddNewPrompt, SetPromptActive
from fastapi import FastAPI, APIRouter, HTTPException, Query
from utils.mongodb_schemas import prompts_collection
import uuid

router = APIRouter()

@router.post('/update_prompt/', tags=['Prompt'])
async def update_prompt(request: UpdatePrompt):
    try:
        prompt_info = prompts_collection.find_one({'space_id': request.space_id})
        if not prompt_info:
            raise HTTPException(status_code=404, detail='Prompt not found')
        
        if request.step not in prompt_info['versions']:
            raise HTTPException(status_code=400, detail=f'Invalid step: {request.step}')
        
        prompts_collection.update_one(
            {'space_id': request.space_id, f'versions.{request.step}.id': request.id},
            {'$set': {f'versions.{request.step}.$.prompt': request.new_prompt}}
        )
        if request.isActive:
            update_prompt_stage = prompts_collection.find_one({'space_id': request.space_id, f'versions.{request.step}.id': request.id})
            if request.step == '1':
                update_field = 'stage_1_prompt'
            elif request.step == '2':
                update_field = 'stage_2_prompt'
            elif request.step == '3':
                update_field = 'broll_prompt'
            elif request.step == '4':
                update_field = 'music_prompt'
            else:
                raise HTTPException(status_code=400, detail='Invalid step')
            matching_prompt = next(
                (prompt for prompt in update_prompt_stage['versions'][request.step] 
                if prompt['id'] == request.id),
                None
            )
            prompts_collection.update_one(
                {'space_id': request.space_id},
                {'$set': {update_field: matching_prompt['prompt']}}
            )
        return {'message': 'Prompt updated successfully'}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An unexpected error occurred: {str(e)}')

@router.get('/fetch_prompts/', tags=['Prompt'])
async def fetch_prompts(step: str = Query(...), space_id: str = Query(...)):
    try:
        space_prompt_data = prompts_collection.find_one({'space_id': space_id})
        if not space_prompt_data:
            raise ValueError('Prompt data not found.')
        prompt_data = [
            {'id': prompt['id'], 'name': prompt['name'], 'active': prompt['active']} 
            for prompt in space_prompt_data['versions'][step]
        ]
        return {'data': prompt_data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to fetch the prompts: {e}')
    
@router.get('/fetch_prompt/', tags=['Prompt'])
async def fetch_prompt(id: str = Query(...), step: str = Query(...), space_id: str = Query(...)):
    try:
        prompt_data = prompts_collection.find_one({'space_id': space_id})
        if not prompt_data:
            raise ValueError('Prompt data not found.')
        for prompt in prompt_data['versions'][step]:
            if id==prompt['id']:
                return {'prompt': prompt['prompt']}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to fetch prompt: {e}')
    
@router.post('/edit_prompt_name/', tags=['Prompt'])
async def edit_prompt_name(request: EditPromptName):
    try:
        prompt_data = prompts_collection.find_one({'space_id': request.space_id})
        if not prompt_data:
            raise ValueError('Prompt data not found.')
        result = prompts_collection.update_one(
            {'space_id': request.space_id, f'versions.{request.step}.id': request.id},
            {'$set': {f'versions.{request.step}.$.name': request.new_name}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail='Failed to rename prompt')
        return {'message': 'Prompt name updated.'}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to rename: {e}')

@router.post('/add_prompt/', tags=['Prompt'])
async def add_prompt(request: AddNewPrompt):
    try:
        prompt_data = prompts_collection.find_one({'space_id': request.space_id})
        if not prompt_data:
            raise ValueError('Prompt data not found')
        
        active_prompt = 'Sample'
        for prompt in prompt_data['versions'][request.step]:
            if prompt['active']:
                active_prompt = prompt['prompt']
                break
        new_prompt_data = {'id': str(uuid.uuid4()), 'name': 'Untitled', 'prompt': active_prompt, 'active': False}
        result = prompts_collection.update_one(
            {'space_id': request.space_id},
            {'$push': {f'versions.{request.step}': new_prompt_data}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail='Failed to add new prompt')
        return {'message': 'New prompt created.', 'id': new_prompt_data['id']}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f'Failed to add new prompt: {e}')
    
@router.post('/set_active/', tags=['Prompt'])
async def set_active(request: SetPromptActive):
    try:
        prompt_data = prompts_collection.find_one({'space_id': request.space_id})
        if not prompt_data:
            raise HTTPException(status_code=404, detail='Prompt data not found')
    
        prompts_collection.update_one(
            {'space_id': request.space_id},
            {'$set': {f'versions.{request.step}.$[].active': False}}
        )
        result = prompts_collection.update_one(
            {'space_id': request.space_id, f'versions.{request.step}.id': request.id},
            {'$set': {f'versions.{request.step}.$.active': True}}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=400, detail='Failed to update active prompt')
        
        update_prompt_stage = prompts_collection.find_one({'space_id': request.space_id, f'versions.{request.step}.id': request.id})
        if request.step == '1':
            update_field = 'stage_1_prompt'
        elif request.step == '2':
            update_field = 'stage_2_prompt'
        elif request.step == '3':
            update_field = 'broll_prompt'
        elif request.step == '4':
            update_field = 'music_prompt'
        else:
            raise HTTPException(status_code=400, detail='Invalid step')
        matching_prompt = next(
            (prompt for prompt in update_prompt_stage['versions'][request.step] 
             if prompt['id'] == request.id),
            None
        )
        prompts_collection.update_one(
            {'space_id': request.space_id},
            {'$set': {update_field: matching_prompt['prompt']}}
        )
        
        new_prompt_data = prompts_collection.find_one({'space_id': request.space_id})
        new_prompts = [
            {'id': prompt['id'], 'name': prompt['name'], 'active': prompt.get('active', False)}
            for prompt in new_prompt_data['versions'][request.step]
        ]
        return {'data': new_prompts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Unexpected error: {str(e)}')