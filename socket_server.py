import socketio
socket_server = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')