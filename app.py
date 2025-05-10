from middleware.middleware import ForwardedHeaderMiddleware, VerifyTokenMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from swagger_ui import custom_openapi
from fastapi import FastAPI

from api.auth.user_auth import router as users_router
from api.spaces.spaces import router as spaces_router
from api.presets.presets import router as presets_router
from api.upload.upload_s3 import router as upload_router
from api.automation.process_automation import router as automation_router
from api.transcript.whisper_model import router as whisper_router
from api.prompts.prompt import router as prompt_router
from api.stage_one.stage_one_api import router as stage_one_router
from api.stage_two.stage_two_api import router as stage_two_router
from api.stage_three.stage_three_api import router as stage_three_router
from api.folders.folders import router as folders_router
from api.fetch.get_clips_apis import router as get_clips_router
from api.fetch.delete_apis import router as delete_stage_clips_router
from api.fetch.fetch_apis import router as fetch_router
from api.fetch.update_apis import router as update_router
from socket_server import socket_server
import socketio, os, glob
os.environ['FFMPEG_BINARY'] = '/usr/bin/ffmpeg'

TEMP_DIRECTORIES = ['transcript_files', 'output_clips', 'remixed_clips', 'project_clips', '.']
def ensure_directories():
    for folder in TEMP_DIRECTORIES:
        if folder != "." and not os.path.exists(folder):
            os.makedirs(folder)

def clean_temp_files():
    for folder in TEMP_DIRECTORIES:
        files_to_delete = glob.glob(os.path.join(folder, '*.mp3')) + glob.glob(os.path.join(folder, '*.mp4'))
        for file in files_to_delete:
            try:
                os.remove(file)
            except Exception:
                pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_directories()
    clean_temp_files()
    yield

fastapi_app = FastAPI(
    title='ClipForge',
    lifespan=lifespan
)
socket_app = socketio.ASGIApp(socket_server)
fastapi_app.openapi = custom_openapi(fastapi_app)
fastapi_app.add_middleware(VerifyTokenMiddleware)
fastapi_app.add_middleware(ForwardedHeaderMiddleware)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

fastapi_app.include_router(users_router)
fastapi_app.include_router(spaces_router)
fastapi_app.include_router(presets_router)
fastapi_app.include_router(upload_router)
fastapi_app.include_router(automation_router)
fastapi_app.include_router(whisper_router)
fastapi_app.include_router(stage_one_router)
fastapi_app.include_router(stage_two_router)
fastapi_app.include_router(stage_three_router)
fastapi_app.include_router(folders_router)
fastapi_app.include_router(get_clips_router)
fastapi_app.include_router(delete_stage_clips_router)
fastapi_app.include_router(fetch_router)
fastapi_app.include_router(prompt_router)
fastapi_app.include_router(update_router)

@socket_server.on("connect")
async def connect(sid, environ, auth):
    pass

@socket_server.on("disconnect")
async def disconnect(sid):
    pass

class CombinedASGI:
    def __init__(self, fastapi_app, socket_app):
        self.fastapi_app = fastapi_app
        self.socket_app = socket_app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            await self.socket_app(scope, receive, send)
        else:
            await self.fastapi_app(scope, receive, send)

app = CombinedASGI(fastapi_app, socket_app)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:app', host='0.0.0.0', port=8000)