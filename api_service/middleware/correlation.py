import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        # Get existing correlation ID or generate a new one
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        
        # Add it to request state for use in application logic
        request.state.correlation_id = correlation_id
        
        # It's better to configure structlog per-request context here if possible,
        # but storing in request.state is the standard starting point.
        
        response = await call_next(request)
        
        # Return correlation ID in the response headers
        response.headers["X-Correlation-ID"] = correlation_id
        return response
