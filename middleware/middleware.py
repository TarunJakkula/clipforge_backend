from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import MutableHeaders
from fastapi.responses import Response, JSONResponse
from datetime import datetime, timedelta
from starlette.requests import Request
from jose import jwt, JWTError
import re

from utils.env_variables import SECRET_KEY, ALGORITHM
from utils.mongodb_schemas import users_collection
from utils.log_errors import logger
class ForwardedHeaderMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        headers = MutableHeaders(scope=request.scope)
        if headers.get('x-forwarded-proto') == 'https':
            request.scope['scheme'] = 'https'
        return await call_next(request)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({'exp': expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
class VerifyTokenMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path_pattern = re.compile(r'^/user_login/?$|^/verify_user/?$|^/docs/?$|^/openapi.json/?$|^/redoc/?$')

        if path_pattern.match(request.url.path):
            return await call_next(request)

        authorization = request.headers.get('Authorization')
        if not authorization or not authorization.startswith('Bearer '):
            return JSONResponse(status_code=401, content={'detail': 'Authorization header is missing or invalid.'})

        token = authorization.split(' ')[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get('sub')
            exp: int = payload.get('exp')

            if not email or not exp:
                return JSONResponse(status_code=401, content={'detail': 'Invalid token payload.'})

            if not users_collection.find_one({'email': email}):
                return JSONResponse(status_code=401, content={'detail': 'User not found.'})

            # Check if token is about to expire and reissue
            current_time = datetime.utcnow()
            remaining_time = datetime.utcfromtimestamp(exp) - current_time
            if remaining_time.total_seconds() < 300:
                new_token = create_access_token(data={'sub': email})
                response = await call_next(request)
                response.headers['X-New-Access-Token'] = new_token
                return response

            request.state.user = {'email': email}
            return await call_next(request)

        except JWTError as e:
            logger.error(f"JWT Decode Error: {str(e)}")
            return JSONResponse(status_code=401, content={'detail': 'Could not validate token.'})