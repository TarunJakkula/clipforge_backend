from utils.env_variables import SECRET_KEY, BACKEND_URL
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.openapi.utils import get_openapi

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
def get_current_user(token: str = Depends(oauth2_scheme)):
    if token != SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"username": "admin"}

def custom_openapi(app):
    def openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            summary='ClipForge is a robust AI-driven video processing platform designed to streamline the creation, editing, and remixing of video content using automated workflows.',
            routes=app.routes,
            terms_of_service='https://swagger.io',
            contact={'email': 'apiteam@swagger.io'},
        )
        openapi_schema["servers"] = [
            {"url": BACKEND_URL, "description": "GPU Instance"},
        ]
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
        for path in openapi_schema["paths"]:
            for method in openapi_schema["paths"][path]:
                openapi_schema["paths"][path][method]["security"] = [{"BearerAuth": []}]

        app.openapi_schema = openapi_schema
        return app.openapi_schema
    return openapi