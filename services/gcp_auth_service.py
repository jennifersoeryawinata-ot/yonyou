from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.oauth2 import id_token
from google.auth.transport import requests
from configs.config import settings

security = HTTPBearer()

class GcpAuthService:
    def verify_gcp_token(self, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
        """
        Dependency untuk memvalidasi OIDC Token dari GCP.
        """
        token = credentials.credentials
        
        try:
            request = requests.Request()
            
            decoded_token = id_token.verify_oauth2_token(
                id_token=token, 
                request=request, 
                audience=settings.EXPECTED_AUDIENCE
            )
            
            
            if decoded_token.get("email") != settings.EXPECTED_SA_EMAIL:
                raise ValueError("Service Account email mismatch")
                
            return decoded_token
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication Failed: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )