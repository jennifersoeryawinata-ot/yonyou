from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging
import time
import re

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        url_str = str(request.url)
        start_time = time.time()
        request_body = await request.body()
        
        response = await call_next(request)
        response_body = b""
        media_type = response.media_type
        
        async for chunk in response.body_iterator:
            response_body += chunk

        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)
        
        request_data = {
            "method": request.method,
            "url": url_str,
            "headers": dict(request.headers),
            "body": request_body.decode("utf-8", errors="ignore"),
        }
        
        response_data = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response_body.decode("utf-8", errors="ignore"),
            "media_type": media_type
        }
        
        log_entry = {
            "method": request_data.get("method"),
            "status": response_data.get("status_code"),
            "url": request_data.get("url"),
            "duration_ms": duration_ms,
            "log_type": "http_trace",
            "http_request": {
                "request_headers": request_data.get("headers"),
                "request_body": request_data.get("body"),
                "response_headers": response_data.get("headers"),
                "response_body": response_data.get("body"),
            }
        }
        logging.info(log_entry)

        return Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=media_type
        )