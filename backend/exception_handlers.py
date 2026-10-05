import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.utils.errors import AppError

logger = logging.getLogger(__name__)

GENERIC_FAILURE = "ระบบประมวลผลไม่สำเร็จ ลองอีกครั้ง"
INVALID_REQUEST = "ข้อมูลที่ส่งมาไม่ถูกต้อง ตรวจสอบค่าที่กรอกแล้วลองอีกครั้ง"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.info("Request validation failed: %s", exc.errors())
        return JSONResponse(
            status_code=422,
            content={"error": "invalid_request", "message": INVALID_REQUEST},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, AppError):
            return JSONResponse(
                status_code=exc.status_code,
                content={"error": exc.code, "message": exc.message},
            )
        if isinstance(exc, HTTPException):
            return await http_exception_handler(request, exc)
        logger.exception("Unhandled API error")
        return JSONResponse(
            status_code=500,
            content={"error": "server_error", "message": GENERIC_FAILURE},
        )
