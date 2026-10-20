import logging
import re
import ssl
import time
import asyncio
import httpx

from jose import jwt, jwk
from jose.utils import base64url_decode
from fastapi import HTTPException, Depends
from utils.exceptions.common_exception import UnauthenticatedException
from schemas.oauth_schema import AccessToken
from configs.config import settings

logger = logging.getLogger(__name__)
 
_cached_token = None
_token_expiry = 0
_token_lock = asyncio.Lock()

class AuthError(Exception):
    def __init__(self, error_msg: str, status_code: int):
        super().__init__(error_msg)

        self.error_msg = error_msg
        self.status_code = status_code

class KeycloakAuthService:
    async def get_public_key(self, token: str):
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f"{settings.KEYCLOAK_BASE_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs")
            if resp.status_code != 200:
                raise AuthError("Problem with Keycloak discovery URL", status_code=404)
            jwks = resp.json()

        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        key_data = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                key_data = key
                break

        if not key_data:
            # raise HTTPException(status_code=401, detail="Rsa key not found")
            raise UnauthenticatedException(message="Rsa key not found")

        return jwk.construct(key_data)

    async def check_token(self, token: str) -> AccessToken:
        try:
            token = re.sub(r"\s+", "", token)
            
            rsa_key = await self.get_public_key(token)
            decode = self.decode_jwt(token, rsa_key)
            azp = decode["azp"]
            roles = decode.get("resource_access", {}).get(azp, {}).get("roles", [])
            
            return AccessToken(
                active=True,
                scope=decode.get("scope", ""),
                exp=decode["exp"],
                client_id=decode.get("client_id", azp),
                is_service_account=decode.get("is_service_account", False),
                id=decode.get("sub"),
                name=decode.get("name", None),
                user_id=decode.get("user_id", None),
                user_email=decode.get("email", None),
                user_name=decode.get("preferred_username", None),
                user_phone_no=decode.get("phone_number", None),
                employee_id=decode.get("employee_id", None),
                employee_nik=decode.get("nik", None),
                authorities=roles,
                actions=[],
            )
        
        except HTTPException as e:
            print(f"CHECK TOKEN EXCEPTION {e.args}", flush=True)
            raise UnauthenticatedException(message=f"Token Ilegal: {str(e)}")
        
    def decode_jwt(self, token, rsa_key):
        try:
            issuer = f"{settings.KEYCLOAK_BASE_URL}/realms/{settings.KEYCLOAK_REALM}"
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                # audience="account",
                issuer=issuer,
                options={"verify_exp": True, "verify_iss": True, "verify_aud": False}
            )

            return payload
        except jwt.ExpiredSignatureError as e:
            logger.error("CHECK TOKEN EXCEPTION", e.args)
            raise UnauthenticatedException()
        except Exception as e:
            logger.error("CHECK TOKEN EXCEPTION", e.args)
            raise UnauthenticatedException()

    async def get_token(self) -> str:
        global _cached_token, _token_expiry

        current_time = time.time()
        
        if _cached_token and current_time < (_token_expiry - 10):
            return _cached_token

        async with _token_lock:
            current_time = time.time()
            if _cached_token and current_time < (_token_expiry - 10):
                return _cached_token

            payload = {
                "grant_type": "client_credentials",
                "client_id": settings.CLIENT_ID,
                "client_secret": settings.CLIENT_SECRET,
            }
            
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{settings.KEYCLOAK_BASE_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token", 
                        data=payload
                    )
                    resp.raise_for_status() 
                    data = resp.json()
                    _cached_token = data.get("access_token")
                    expires_in = data.get("expires_in", 300)
                    _token_expiry = current_time + expires_in
                    
                    return _cached_token

            except httpx.HTTPStatusError as e:
                print("Status:", e.response.status_code)
                print("Response:", e.response.text)
                raise

            except httpx.HTTPError as e:
                print("HTTP Error:", repr(e))
                raise