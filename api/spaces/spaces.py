from fastapi import HTTPException, Query
from models.pydantic_models import *
from utils.mongodb_schemas import *
from fastapi import APIRouter
import uuid

router = APIRouter()

@router.post('/create_space/', tags=['Spaces'])
async def create_space(request: SpaceRequest):
    if not users_collection.find_one({'user_id': request.user_id}):
        raise HTTPException(status_code=401, detail='User not found')

    try:
        space_id = str(uuid.uuid4())
        new_space = {
            'space_id': space_id,
            'colour_code': request.colour_code,
            'name': request.name,
            'user_id': request.user_id
        }
        spaces_collection.insert_one(new_space)
        with open('api/auth/prompts/stage_1_prompt.txt', 'r') as f:
            static_stage_1_prompt = f.read()
        with open('api/auth/prompts/stage_2_prompt.txt', 'r') as f:
            static_stage_2_prompt = f.read()
        with open('api/auth/prompts/broll_prompt.txt', 'r') as f:
            broll_prompt = f.read()
        with open('api/auth/prompts/music_prompt.txt', 'r') as f:
            music_prompt = f.read()
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
        return {'message': 'Space created successfully'}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Space not created :{e}')

@router.post('/update_space/', tags=['Spaces'])
async def update_space(request: UpdateSpaceRequest):
    existing_user = users_collection.find_one({'user_id': request.user_id})
    if not existing_user:
        raise HTTPException(status_code=404, detail='User not found')
    if not spaces_collection.find_one({'space_id': request.space_id, 'user_id': request.user_id}):
        raise HTTPException(status_code=404, detail='Space not found with this user')
    
    try:
        spaces_collection.update_one(
            {'space_id': request.space_id},
            {'$set': {
                'colour_code': request.colour_code,
                'name': request.name
            }}
        )
        return {'message': 'Space updated successfully'}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Space not updated :{e}')
    
@router.get('/get_spaces/', tags=['Spaces'])
async def get_space(user_id : str =  Query(...)):
    user = users_collection.find_one({'user_id': user_id})
    if not user:
        raise HTTPException(status_code=404, detail='User not found')

    try:
        spaces = []
        for space in list(spaces_collection.find({'user_id': user_id})) :
            temp = {
                'space_id':space['space_id'],
                'color':space['colour_code'],
                'name':space['name']
            }
            spaces.append(temp)
        return {'spaces' : spaces}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Error fetching space :{e}')
    
@router.delete('/delete_space/', tags=['Spaces'])
async def delete_space(user_id: str = Query(...), space_id: str = Query(...)):
    user = users_collection.find_one({'user_id': user_id})
    if not user:
        raise HTTPException(status_code=401, detail='User not found')

    try:
        delete_result = spaces_collection.delete_one({'space_id': space_id, 'user_id': user_id})
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail='Error in deleting space')
        return {'message': 'Space deleted successfully', 'space_id': space_id}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f'Unable to delete space :{e}')