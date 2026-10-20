from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

from configs.config import settings
from schemas.oauth_schema import AccessToken
from services.oauth_service import OauthService

token_auth_scheme = HTTPBearer()


class Permission:
    def get_cred_exception(self, status_code: int, msg: str) -> HTTPException:
        credentials_exception = HTTPException(
            status_code=status_code,
            detail=msg,
            headers={"WWW-Authenticate": "Bearer"},
        )
        return credentials_exception

    async def is_allowed(self, role: str, token: str) -> AccessToken:
        at = await OauthService().check_token(token.credentials)

        if role in at.authorities:
            return at
        else:
            raise self.get_cred_exception(
                status.HTTP_403_FORBIDDEN, "Not Authorized")

    async def is_allowed_user(self, request: Request, token: str = Depends(token_auth_scheme)) -> AccessToken:
        if token.credentials == settings.OAUTH2_TOKEN:
            request.state.access_token = AccessToken(active=True)
            return AccessToken(active=True)
        at: AccessToken = await self.is_allowed(settings.OAUTH_ROLE, token)
        request.state.access_token = at

        return at

    async def is_allowed_client_fetch_worker(self, request: Request, token: str = Depends(token_auth_scheme)) -> AccessToken:
        at: AccessToken = await self.is_allowed('PIK_EXP_FETCH_WORKER', token)
        request.state.access_token = at

        if request.state.access_token.user_id is not None:
            raise self.get_cred_exception(
                status.HTTP_403_FORBIDDEN, "Not Authorized")

        return at
