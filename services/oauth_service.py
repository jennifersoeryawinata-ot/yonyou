import requests
from fastapi import HTTPException

from configs.config import settings
from schemas.oauth_schema import AccessToken, OauthUser


class OauthService:
    OAUTH_BASE_URL = settings.OAUTH2_URL
    OAUTH_DEFAULT_TOKEN = settings.OAUTH2_TOKEN

    NOT_AUTHORIZED = "Not authenticated"
    NOT_FOUND = "Not Found"
    CONNECTION_FAILED = "Cannot create connection to authentication server."

    async def check_token(self, token) -> AccessToken:
        try:
            url = f'{self.OAUTH_BASE_URL}/oauth/check_token/'
            headers = {'Authorization': f'Bearer {self.OAUTH_DEFAULT_TOKEN}'}
            body = {'token': token}
            response = requests.post(url=url, headers=headers, data=body, timeout=None)
            if response.status_code == 200:
                r = response.json()
                if r['active'] == False:
                    raise HTTPException(status_code=403, detail='Not authorized')

                return AccessToken(**r)
            else:
                raise HTTPException(status_code=403, detail='Not authorized')
        except:
            raise HTTPException(status_code=400, detail='Something wrong. Please contact developer.')

    async def check_user_by_email_or_phone(self, email: str, phone: str | None = None) -> dict:
        url = self.OAUTH_BASE_URL + '/api/users/byemailormobile' + '/' + email
        url = url if phone is None else url + '/' + phone.replace('+', '')
        headers = {'Authorization': f'Bearer {self.OAUTH_DEFAULT_TOKEN}'}
        response = requests.get(url=url, headers=headers, timeout=None)

        return response.json()['data'] if response.json()['data'] != None else {'detail': ''}

    async def register_user_oauth(self, body: dict) -> OauthUser:
        url_create_user = self.OAUTH_BASE_URL + '/api/users/'

        headers = {
            'Authorization': 'Bearer ' + self.OAUTH_DEFAULT_TOKEN,
            'Content-Type': 'Application/Json'
        }

        response = requests.post(url_create_user, json=body, headers=headers, timeout=None)
        if response.status_code == 201:
            data = response.json()['data']
            return OauthUser(**data)
        else:
            raise HTTPException(status_code=400, detail='Something wrong. Please contact developer.')

    async def update_user_oauth(self, body: dict, id: str) -> OauthUser:
        url_update_user = self.OAUTH_BASE_URL + '/api/users/' + id + '/'

        headers = {
            'Authorization': 'Bearer ' + self.OAUTH_DEFAULT_TOKEN,
            'Content-Type': 'Application/Json'
        }

        response = requests.put(url_update_user, json=body, headers=headers, timeout=None)
        if response.status_code == 200:
            data = response.json()['data']
            return OauthUser(**data)
        else:
            raise HTTPException(status_code=400, detail='Something wrong. Please contact developer.')

    async def get_user_by_id(self, oauth_id):
        url = self.OAUTH_BASE_URL + '/api/users/' + oauth_id

        headers = {
            'Authorization': 'Bearer ' + self.OAUTH_DEFAULT_TOKEN
        }

        response = requests.get(url, headers=headers, timeout=None)
        return response.json()['data'] if response.json()['data'] != None else {'detail': ''}
