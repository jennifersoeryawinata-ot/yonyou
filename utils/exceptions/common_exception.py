import logging

from fastapi.responses import JSONResponse
from pydantic import ValidationError
from stringcase import pascalcase
from typing import Any, Dict, Optional, Type, TypeVar
from fastapi.exceptions import HTTPException, RequestValidationError, ResponseValidationError
from fastapi import FastAPI, Request, status as http_status

from models.base_model import SQLModel
from schemas.response_schema import ResponseSchema
from utils.errors import format_errors

ModelType = TypeVar("ModelType", bound=SQLModel)
T = TypeVar("T")

class BadRequestException(HTTPException):
    def __init__(
        self,
        message: str | None = None,
        data: Dict[str, Any] | None = None,
        headers: Dict[str, Any] | None = None
    ):
        if data:
            standarized = ResponseSchema(
                status='error',
                code=http_status.HTTP_400_BAD_REQUEST,
                message=message,
                data=data,
                errors=None
            )

            super().__init__(
                status_code=standarized.code,
                detail=standarized.model_dump(),
                headers=headers
            )
        
            return
        
        standarized = ResponseSchema(
            status='error',
            code=http_status.HTTP_400_BAD_REQUEST,
            message=message,
            data=None,
            errors=None
        )

        super().__init__(
            status_code=standarized.code,
            detail=standarized.model_dump(),
            headers=headers
        )

class NotFoundException(HTTPException):
    def __init__(
        self,
        model: Optional[Type[ModelType]],
        id: str | None = None,
        message: str | None = None,
        headers: Dict[str, Any] | None = None
    ):
        if id:
            standarized = ResponseSchema(
                status='error',
                code=http_status.HTTP_404_NOT_FOUND,
                message=f"Model {pascalcase(model.__name__)} with id '{id}' is not found",
                data=None,
                errors=None
            )

            super().__init__(
                status_code=standarized.code,
                detail=standarized.model_dump(),
                headers=headers
            )
            
            return
        
        if message:
            standarized = ResponseSchema(
                status='error',
                code=http_status.HTTP_404_NOT_FOUND,
                message=message,
                data=None,
                errors=None
            )

            super().__init__(
                status_code=standarized.code,
                detail=standarized.model_dump(),
                headers=headers
            )
            
            return
        
        standarized = ResponseSchema(
            status='error',
            code=http_status.HTTP_404_NOT_FOUND,
            message=f"No data for {pascalcase(model.__name__)} found. Please register or add new {pascalcase(model.__name__)} data first.",
            data=None,
            errors=None
        )

        super().__init__(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=standarized.model_dump(),
            headers=headers
        )

class InternalServerErrorException(HTTPException):
    def __init__(self, model: Type[ModelType], message: Optional[str] = None, headers: Optional[Dict[str, Any]] = None):
        if message:
            standarized = ResponseSchema(
                status='error',
                code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=message,
                data=None,
                errors=None
            )

            super().__init__(
                status_code=standarized.code,
                detail=standarized.model_dump(),
                headers=headers
            )
        
        if model:
            standarized = ResponseSchema(
                status='error',
                code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Something wrong happened when processing data {pascalcase(model.__name__)}. Please try again or contact Administrator.",
                data=None,
                errors=None
            )

            super().__init__(
                status_code=standarized.code,
                detail=standarized.model_dump(),
                headers=headers
            )

        standarized = ResponseSchema(
            status='error',
            code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            message='Something wrong happened when processing the request. Please try again or contact Administrator.',
            data=None,
            errors=None
        )

        super().__init__(
            status_code=standarized.code,
            detail=standarized.model_dump(),
            headers=headers
        )

class ConflictException(HTTPException):
    def __init__(self, data: Optional[Dict[str, Any]], model: Type[ModelType], id: str, message: Optional[str] = None, headers: Optional[Dict[str, Any]] = None):
        if message:
            standarized = ResponseSchema(
                status='error',
                code=http_status.HTTP_409_CONFLICT,
                message=message,
                data=data,
                errors=None
            )

            super().__init__(
                status_code=standarized.code,
                detail=standarized.model_dump(),
                headers=headers
            )

            return
        
        if model and id:
            standarized = ResponseSchema(
                status='error',
                code=http_status.HTTP_409_CONFLICT,
                message=f"Error when processing data {pascalcase(model.__name__)}. Existing duplicate data found with id : '{id}'",
                data=data,
                errors=None
            )

            super().__init__(
                status_code=standarized.code,
                detail=standarized.model_dump(),
                headers=headers
            )

            return

        standarized = ResponseSchema(
            status='error',
            code=http_status.HTTP_409_CONFLICT,
            message=f"Existing duplicate data found with id : '{id}'",
            data=data,
            errors=None
        )

        super().__init__(
            status_code=standarized.code,
            detail=standarized.model_dump(),
            headers=headers
        )

class ValidationException(HTTPException):
    def __init__(
        self,
        model: Type[ModelType],
        exc: RequestValidationError | ValidationError,
        headers: Dict[str, Any] | None = None
    ):
        standarized = ResponseSchema(
            code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            status='error',
            message=f"Failed to process data, validation error on {pascalcase(model.__name__)}",
            data=None,
            errors=format_errors(exc)
        )

        super().__init__(
            status_code=standarized.code,
            detail=standarized.model_dump(),
            headers=headers
        )

class UnauthenticatedException(HTTPException):
    def __init__(self, message: Optional[str] = None, headers: Dict[str, Any] | None = None):
        standarized = ResponseSchema(
            status='error',
            code=http_status.HTTP_401_UNAUTHORIZED,
            message=f"Unauthenticated. Session expired / not found, please login to start action. Detail: {message}",
            headers=headers,
            errors=None
        )

        super().__init__(
            status_code=standarized.code,
            detail=standarized.model_dump(),
            headers=headers
        )
class UnauthorizedException(HTTPException):
    def __init__(self, message: Optional[str] = None, headers: Dict[str, Any] | None = None):
        standarized = ResponseSchema(
            status='error',
            code=http_status.HTTP_403_FORBIDDEN,
            message="Action forbidden. You aren't allowed to access this feature / action",
            headers=headers,
            errors=None
        )

        super().__init__(
            status_code=standarized.code,
            detail=standarized.model_dump(),
            headers=headers
        )

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
                
        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "code": http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Something wrong happened when processing the request. Please try again or contact Administrator.",
                "data": None,
                "errors": None
            }
        )
    
    @app.exception_handler(ResponseValidationError)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        
        #logger.error(f"Unhandled Exception :\n %s", str(exc), exc_info=True)
        
        return JSONResponse(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "code": http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": "Something wrong happened when processing the request. Please try again or contact Administrator.",
                "data": None,
                "errors": None
            }
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException
    ) -> JSONResponse:
        if isinstance(exc.detail, dict):
            return JSONResponse(
                status_code=exc.status_code,
                content=exc.detail,
                headers=exc.headers
            )

        return JSONResponse(
            status_code=exc.status_code or http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "status": "error",
                "code": exc.status_code or http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": exc.detail or "Something wrong happened when processing the request. Please try again or contact Administrator.",
                "data": None,
                "errors": None
            },
            headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        #logger.warning(f"Request Validation Error :\n %s", str(exc), exc_info=True)

        return JSONResponse(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "status": "error",
                "code": http_status.HTTP_422_UNPROCESSABLE_CONTENT,
                "message": "Failed to process data, validation error on request",
                "data": None,
                "errors": [e.model_dump() for e in format_errors(exc)]
            }
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: ValidationError
    ) -> JSONResponse:
        #logger.warning(f"Validation Error :\n %s", str(exc), exc_info=True)
        
        return JSONResponse(
            status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={
                "status": "error",
                "code": http_status.HTTP_422_UNPROCESSABLE_CONTENT,
                "message": "Failed to process data, validation error on request",
                "data": None,
                "errors": [e.model_dump() for e in format_errors(exc)]
            }
        )
