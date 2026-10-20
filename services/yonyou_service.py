import json
from fastapi import HTTPException
from yonbip_open_api_sdk import request_opt, token_opt
from configs.config import settings

class YonyouBaseService:
    def __init__(self):
        self.token_info = {
            "app_key": settings.YONYOU_APP_KEY,
            "app_secret": settings.YONYOU_APP_SECRET,
            "host_url": settings.YONYOU_BASE_URL
        }
        self.tenant_id = settings.YONYOU_TENANT_ID

    async def get_token(self) -> str:
        """Fetches and handles the self-built app gateway access token."""
        return token_opt.opt_self_token(
            settings.YONYOU_APP_KEY,  
            settings.YONYOU_APP_SECRET, 
            settings.YONYOU_BASE_URL
        )

    async def _request(self, method: str, path: str, data: dict = None, params: dict = None):
        """Internal wrapper handling authentication headers, tenant routing, and SDK execution."""
        
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        
        # Merge baseline yonyou requirements
        request_params = {"tenantId": self.tenant_id}
        if params:
            request_params.update(params)

        payload = json.dumps(data) if data else "{}"

        response = request_opt.opt_self_app_request(
            method=method.lower(),
            request_url=path,
            header=headers,
            data=payload,
            params=request_params,
            token_info=self.token_info
        )

        if response.status_code > 204:
            raise HTTPException(status_code=response.status_code, detail="ERROR")

        return response.json()