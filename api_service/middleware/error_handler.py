from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

logger = structlog.get_logger()

async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error("HTTP Exception", status_code=exc.status_code, detail=exc.detail, path=request.url.path)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": "HTTP_ERROR",
            "message": str(exc.detail),
            "details": {}
        }
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Validation Error", errors=exc.errors(), path=request.url.path)
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Validation error in request parameters or body",
            "details": {"errors": exc.errors()}
        }
    )

async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Internal Server Error", error=str(exc), path=request.url.path, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "details": {"reason": str(exc)}
        }
    )

def setup_exception_handlers(app):
    app.add_exception_handler(StarletteHTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
