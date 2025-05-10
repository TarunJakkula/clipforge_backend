from pydantic import BaseModel, EmailStr
from typing import List, Optional

class UserLoginRequest(BaseModel):
    email: EmailStr

class OTPVerifyRequest(BaseModel):
    otp_id: str
    email: EmailStr
    otp: str
    
class EditUserProfile(BaseModel) :
    user_id: str
    user_name: str
    
class SpaceRequest(BaseModel):
    user_id: str
    colour_code: str
    name: str
    
class UpdateSpaceRequest(BaseModel):
    user_id: str
    space_id: str
    colour_code: str
    name: str
    
class CreatePresetRequest(BaseModel):
    space_id: str
    name: str
    options: dict
    color: str
    media_ids:dict
    
class UpdatePresetRequest(BaseModel):
    space_id: str
    preset_id: str
    name: str
    options: dict
    color: str
    media_ids:dict
    
class CompleteUploadRequest(BaseModel):
    user_id: str
    space_id: str
    file_name: str
    upload_id: str
    parts: List[dict]
    file_id: str
    category: str
    tags: Optional[list] = None
    parent_id: Optional[str] = None
    aspect_ratio: Optional[str] = None
    
class TranscriptRequest(BaseModel):
    clip_id: str
    
class UpdateStage1Prompt(BaseModel):
    space_id: str
    prompt: str

class UpdateStage2Prompt(BaseModel):
    space_id: str
    prompt: str
    
class GenerateClipsRequest(BaseModel) :
    space_id: str
    clip_id: str
    
class FetchPossibleClips(BaseModel):
    clip_id: str
    
class GenerateRemixedClips(BaseModel):
    space_id: str
    clip_id: str
    
class CreateFolder(BaseModel):
    folder_name: str
    parent_id: str
    category: str
    space_id: str
    
class Rename(BaseModel):
    id: str
    name: str
    category: str
    
class Move(BaseModel):
    sour_id: str
    dest_id: str
    category: str

class UpdatePrompt(BaseModel):
    id: str
    new_prompt: str
    step: str
    space_id: str
    isActive: bool
    
class FetchBrollAndAdd(BaseModel):
    space_id: str
    subclip_id: str
    
class AddBrollMusicPresets(BaseModel):
    space_id: str
    subclip_id: str
    
class EditTags(BaseModel):
    file_id: str
    category: str
    tags: list
    
class AutomateProcess(BaseModel):
    space_id: str
    clip_id: str
    
class AccessFolder(BaseModel):
    folder_id: str
    space_id: str
    spaces: list
    category: str
    
class AccessPreset(BaseModel):
    preset_id: str
    space_id: str
    spaces: list
    
class AutomationRestart(BaseModel):
    task_id: str
    
class EditPromptName(BaseModel):
    id: str
    new_name: str
    step: str
    space_id: str
    
class AddNewPrompt(BaseModel):
    step: str
    space_id: str
    
class SetPromptActive(BaseModel):
    id: str
    step: str
    space_id: str
class AdminUserLoginRequest(BaseModel):
    email: EmailStr
class AdminOTPVerifyRequest(BaseModel):
    otp_id: str
    otp: str
    email: EmailStr
    user_id: str
class  UserAccess(BaseModel):
    user_id: str