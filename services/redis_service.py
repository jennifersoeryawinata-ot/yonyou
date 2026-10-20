
from typing import override
from configs.config import settings
from redis import Redis 

class RedisService(Redis):
    def __init__(self):
        self.default_expire_time = 86400 # 1 hari 
        
        super().__init__(
            host=settings.REDIS_HOST, 
            port=settings.REDIS_PORT, 
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10,
            health_check_interval=30,
        )

    # @override
    # def set(self,key,value,ex=None):

        


redis_service = RedisService()