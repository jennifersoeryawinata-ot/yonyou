from decimal import Decimal
import logging
import math

from fastapi import status as http_status
from fastapi_pagination import Page, Params
from fastapi_pagination.bases import AbstractPage, AbstractParams
from pydantic import BaseModel, ConfigDict, Field, create_model, field_serializer
from typing import Any, Dict, Generic, Sequence, Type, TypeVar

T = TypeVar("T")

logs = logging.getLogger(__name__)

class DropdownResultSchema(BaseModel):
    id: str = Field(...,
        description="Id of the model",
        examples=["MI01KP7H5RVRGCSCQY3ESNFBQW66"]
    )
    name: str= Field(...,
        description="Displayed name for the dropdown",
        examples=["Ayam Goreng Mor"]
    )

    model_config = {"from_attributes": True}
    
class ErrorDetailSchema(BaseModel):
    field: str = Field(
        ...,
        description="Field name which causes the error",
        examples=["email"]
    )
    message: str = Field(
        ...,
        description="Description of the error",
        examples=["Invalid email format"]
    )

class PaginationMeta(BaseModel):
    curr_page: int
    prev_page: int | None = 1
    next_page: int | None
    per_page: int
    pages: int
    total: int | None

class PaginationData(BaseModel, Generic[T]):
    items: Sequence[T]
    meta: PaginationMeta

class ResponseSchema(BaseModel, Generic[T]):
    """
    Standard response format for all API endpoints.
    """

    status: str | None = Field(
        ...,
        description="Indicator for response status (e.g. ok, created, error)",
        examples=["ok", "created", "error"]
    )

    code: int | None = Field(
        ...,
        description="HTTP status code for the response",
        examples=[
            http_status.HTTP_200_OK,
            http_status.HTTP_201_CREATED,
            http_status.HTTP_400_BAD_REQUEST,
            http_status.HTTP_409_CONFLICT,
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            http_status.HTTP_422_UNPROCESSABLE_CONTENT,
        ]
    )

    message: str | None = Field(
        default='Request completed successfully',
        description="User readable response message",
        examples=["Request completed successfully"]
    )

    data: T | None = Field(
        default=None,
        description="Requested data (if available)"
    )

    errors: list[ErrorDetailSchema] | None = Field(
        default=None,
        description="List of all validation errors if request failed because of invalid parameters"
    )


    model_config = ConfigDict(from_attributes=True)
	
    # 20260402 Commented because this removes trailing zero in decimals (e.g. "1000.00" become "1000")
    # @field_serializer("data", mode="plain")
    # def serialize_data(self, data: Any, _info):
    #     return self._recursive_decimal_format(data)

    def _recursive_decimal_format(self, obj: Any) -> Any:
        """Recursively finds Decimals in lists/dicts and formats them."""
        if isinstance(obj, Decimal):
            return format(obj.normalize(), 'f')
        if isinstance(obj, list):
            return [self._recursive_decimal_format(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._recursive_decimal_format(v) for k, v in obj.items()}
        # If it's a Pydantic model instance, convert to dict first
        if isinstance(obj, BaseModel):
            return self._recursive_decimal_format(obj.model_dump())
        return obj


### Setup Pagination 

class PaginationLink(BaseModel):
    """
    Setup for build URL prev/next 
    """
    self: str
    first: str
    last: str
    prev: str | None = None
    next: str | None = None

class PaginationMeta(BaseModel):
    curr_page: int
    prev_page: int | None = 1
    next_page: int | None
    per_page: int
    pages: int
    total: int | None
    # header: T | None
    links: PaginationLink | None = None

class PaginationData(BaseModel, Generic[T]):
    items: Sequence[T]
    meta: PaginationMeta

# extend ke JsonContentStandardizedSchema dan juga AbstractPage untuk fungsional fastapi_pagination 
class PageDataSchema(AbstractPage[T], ResponseSchema[T], Generic[T]):

    message: str = "Successfully fetched pagination."

class ResponsePageSchema(AbstractPage[T], Generic[T]):
    status: str = "ok"
    code: int = 200
    message: str = ""
    data: PaginationData[T]
    errors: Any | None = None

    __params_type__ = Params

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        total: int,
        params: Params, # Gunakan Params langsung agar mempermudah akses .page dan .size
    ) -> "ResponsePageSchema[T]":
        pages = math.ceil(total / params.size) if params.size > 0 else 0
        
        return cls(
            data=PaginationData(
                items=items,
                meta=PaginationMeta(
                    curr_page=params.page,
                    prev_page=params.page - 1 if params.page > 1 else None,
                    next_page=params.page + 1 if params.page < pages else None,
                    per_page=params.size,
                    pages=pages,
                    total=total,
                    links=None
                )
            )
        )

class GetResponseBaseSchema(ResponseSchema[T], Generic[T]):
    message: str = "Successfully fetched data."

class GetResponsePaginatedSchema(ResponsePageSchema[T], Generic[T]):
    message: str = "Successfully fetched data."

class PostResponseSchema(ResponseSchema[T], Generic[T]):
    message: str = "Data successfully recorded"

class PutResponseSchema(ResponseSchema[T], Generic[T]):
    message: str = "Data updated successfully"

class DeleteResponseSchema(ResponseSchema[T], Generic[T]):
    message: str = "Data deleted successfully"

class UnprocessableEntityResponseSchema(ResponseSchema[T], Generic[T]):
    message: str = "Some data did not pass requirement check"

class InternalServerErrorResponseSchema(ResponseSchema[T], Generic[T]):
    message: str = "Something wrong happened when processing the request. Please try again or contact Administrator."

def create_response(
    data: Any,
    message: str | None = None,
    status: str = "ok",
    code: int = 200,
    errors: Any | None = None
):
    # Jika data sudah merupakan instance dari ResponsePageSch (hasil dari paginate)
    if isinstance(data, ResponsePageSchema):
        if message:
            data.message = message
        data.status = status
        data.code = code
        data.errors = errors
        return data
    
    # Untuk response standar non-paginated
    body_response = {
        "status": status,
        "code": code,
        "message": message or "Success",
        "data": data,
        "errors": errors
    }

    # It returns a dictionary to avoid double
    # validation https://github.com/tiangolo/fastapi/issues/3021
    return dict((k, v) for k, v in body_response.items() if v is not None)