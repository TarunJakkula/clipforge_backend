from utils.env_variables import MONGO_CLIENT
from pymongo import MongoClient

client = MongoClient(MONGO_CLIENT)
db = client['ClipForge']
otp_collection = db['otp']
users_collection = db['users']
spaces_collection = db['spaces']
clips_collection = db['clips']
subclips_collection = db['subclips']
remixed_clips_collection = db['remixed_clips']
brolls_collection = db['broll']
music_collection = db['music']
presets_collection = db['presets']
folders_collection = db['folders']
prompts_collection = db['prompts']
tags_collection = db['tags']
projects_collection = db['projects']
tasks_collection = db['tasks']

otp_collection.create_index('expiry_time', expireAfterSeconds=0)