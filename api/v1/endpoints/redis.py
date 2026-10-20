



from schemas.response_schema import create_response
from services.redis_service import redis_service
from fastapi import APIRouter
routes = APIRouter()


@routes.post("/", name="Test Publish Data to Redis")
async def test_publish_data(
    key:str,
    value:str,
):
    redis_service.instance.set(key, value, ex=20)
    return create_response(data=None)

@routes.get("/{key}", name="Get Redis Data")
async def get_redis_data(
    key:str
):
    return create_response(data=redis_service.instance.get(key))
