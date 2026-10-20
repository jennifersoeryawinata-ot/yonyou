

from api.v1.endpoints import redis
from fastapi.responses import ORJSONResponse

from api.v1.endpoints import role
from fastapi import APIRouter, Depends

from api.v1.endpoints import worker
from services.gcp_auth_service import GcpAuthService

api_router = APIRouter(prefix="/api/v1",)
# api_router = APIRouter(prefix="/api/v1", dependencies=[Depends(Permission().get_auth_context)])
oidc_router = APIRouter(prefix="/oidc/v1", dependencies=[Depends(GcpAuthService().verify_gcp_token)], default_response_class=ORJSONResponse)

api_router.include_router(worker.router, prefix="/worker", tags=["Worker"])
api_router.include_router(role.router, prefix="/role", tags=['Role'])

api_router.include_router(redis.routes, prefix="/redis", tags=["Redis Sample"])
