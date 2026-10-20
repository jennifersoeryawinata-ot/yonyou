import json
import logging
from typing import Dict, Any, Optional
from fastapi import HTTPException
import httpx
from configs.config import settings

logger = logging.getLogger(__name__)

class RabbitMQService:
    """
    Stateless wrapper with an internal connection pool.
    Handles high-frequency HTTP publishing to RabbitMQ efficiently.
    """
    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        """Lazily initializes and reuses the HTTP connection pool."""
        if cls._client is None or cls._client.is_closed:
            cls._client = httpx.AsyncClient(
                base_url=settings.RABBITMQ_BASE_URL,
                auth=(settings.RABBITMQ_USER, settings.RABBITMQ_PASS),
                verify=False, # Disables SSL certificate verification
                timeout=5.0,
                # Pool settings optimized for 10+ req/min
                limits=httpx.Limits(
                    max_keepalive_connections=10, # Keeps TCP sockets open
                    max_connections=30,
                    keepalive_expiry=30.0         # Recycles idle sockets every 30s
                )
            )
            logger.info("Initialized RabbitMQ HTTP connection pool.")
        return cls._client

    @classmethod
    async def close(cls) -> None:
        """Closes the connection pool on app shutdown."""
        if cls._client and not cls._client.is_closed:
            await cls._client.aclose()
            logger.info("Closed RabbitMQ HTTP connection pool.")

    @classmethod
    async def publish(
        cls,
        payload: dict,
        exchange: str = settings.RABBITMQ_EXCHANGE_NAME,
        routing_key: str = "firebase.push",
        delivery_mode: int = 2
    ) -> bool:
        """
        Static async publisher method.
        """

        client = cls.get_client()
        endpoint = f"/api/exchanges/{settings.RABBITMQ_VHOST}/{exchange}/publish"

        request_body = {
            "properties": {"delivery_mode": delivery_mode},  # Persistent
            "routing_key": routing_key,
            "payload": payload.model_dump_json(),
            "payload_encoding": "string",
        }

        try:            
            response = await client.post(endpoint, json=request_body)
            response.raise_for_status()

            result = response.json()
            routed = result.get("routed", False)
            
            if not routed:
                logger.warning(f"Notification published, but no queue bound to '{routing_key}'")

            return routed

        except httpx.HTTPError as e:
            logger.error(f"Failed to publish push notification via HTTP: {e}")
            raise e