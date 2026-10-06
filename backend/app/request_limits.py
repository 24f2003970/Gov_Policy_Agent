"""Bound small API bodies before JSON parsing; raw uploads retain streaming limits."""
from uuid import uuid4
import re
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.responses import JSONResponse

API_BODY_BYTES = 64 * 1024


class BodyLimitMiddleware:
    def __init__(self, app, upload_path=None):
        self.app, self.upload_path = app, upload_path

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or (scope['method'] == 'POST' and scope['path'] == self.upload_path):
            return await self.app(scope, receive, send)
        async def reject(status, code, message):
            request_id = str(uuid4())
            response = JSONResponse({'error': {'code': code, 'message': message, 'request_id': request_id}}, status_code=status,
                                    headers={'X-Request-ID': request_id, 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
            await response(scope, receive, send)
        lengths = [v for k,v in scope['headers'] if k.lower() == b'content-length']
        if lengths:
            if len(lengths) != 1 or not lengths[0].isdigit():
                return await reject(400, 'invalid_content_length', 'Invalid Content-Length')
            if len(lengths[0]) > 16 or int(lengths[0]) > API_BODY_BYTES:
                return await reject(413, 'request_body_limit', 'Request body exceeds 65536-byte limit')
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect': return
            data = message.get('body', b'')
            if len(body) + len(data) > API_BODY_BYTES:
                return await reject(413, 'request_body_limit', 'Request body exceeds 65536-byte limit')
            body.extend(data)
            if not message.get('more_body', False): break
        delivered = False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()
        await self.app(scope, replay, send)


class StrictHostMiddleware(TrustedHostMiddleware):
    async def __call__(self, scope, receive, send):
        if scope['type'] in ('http', 'websocket'):
            hosts = [v for k,v in scope['headers'] if k.lower() == b'host']
            # TrustedHost alone splits at ':', so a path after the port needs rejection first.
            if len(hosts) != 1 or not re.fullmatch(rb'[A-Za-z0-9.-]+(?::[0-9]{1,5})?', hosts[0]):
                if scope['type'] == 'websocket':
                    return await send({'type': 'websocket.close', 'code': 1008})
                return await JSONResponse({'error': {'code': 'invalid_host', 'message': 'Invalid Host header'}}, status_code=400)(scope,receive,send)
        await super().__call__(scope,receive,send)
