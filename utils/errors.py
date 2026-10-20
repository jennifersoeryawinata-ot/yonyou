from sys import prefix

from pydantic import ValidationError
from fastapi.exceptions import RequestValidationError
from schemas.response_schema import ErrorDetailSchema

def format_errors(e: ValidationError | RequestValidationError) -> list[ErrorDetailSchema]:
    errors = list()
    prefixes = ["Value error, ", "Assertion failed, ", "Input should be "]

    for err in e.errors():
        loc = err.get("loc", ())

        if loc and loc[0] in ("body", "query", "path", "header"):
            loc = loc[1:]
        
        field = "." .join(str(l) for l in loc)
        
        cleaned_msg = (
            err.get("msg", "").replace(prefix, "")
            for prefix in prefixes 
            if err.get("msg", "").startswith(prefix)
        )

        error_field = ErrorDetailSchema(
            field=field,
            message=next(cleaned_msg, err.get("msg", "Invalid input"))
        )
        
        errors.append(error_field)

    return errors