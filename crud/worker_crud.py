import random
import string

from fastapi import HTTPException, Request
from fastapi.security import HTTPBearer
from sqlmodel import and_, select
from sqlmodel.ext.asyncio.session import AsyncSession

import crud
from configs.config import settings
from crud.base_crud import CRUDBase
from models import Role, Worker
from schemas.oauth_schema import OauthUser
from schemas.worker_schema import WorkerCreateUpdateSch
from services.oauth_service import OauthService
from utils.phone_formatter import change_phone_format

token_auth_scheme = HTTPBearer()


class CRUDWorker(CRUDBase[Worker, WorkerCreateUpdateSch, WorkerCreateUpdateSch]):
    async def get(
        self,
        *,
        id: str,
        db_session: AsyncSession | None = None,
        current_worker: Worker | None = None,
    ) -> Worker | None:
        db_session = db_session or super().get_db().session
        query = select(self.model).where(self.model.id == id)

        if current_worker is not None:
            if current_worker.is_admin and current_worker.is_super_admin == False:
                query = query.filter(
                    and_(
                        Worker.id.notin_([current_worker.id]),
                        Role.name.notin_(['ADMIN', 'SUPER_ADMIN']),
                    )
                )
            elif current_worker.is_super_admin == False:
                query = query.filter(
                    and_(
                        Worker.id == current_worker.id,
                    )
                )

        response = await db_session.exec(query)
        return response.scalar_one_or_none()

    async def get_by_email(
            self, *, email: str,
            db_session: AsyncSession | None = None) -> Worker:
        db_session = db_session or super().get_db().session
        obj = await db_session.exec(select(Worker).where(Worker.email == email))

        return obj.scalar_one_or_none()

    async def get_by_phone(
            self, *, phone: str,
            db_session: AsyncSession | None = None) -> Worker:
        db_session = db_session or super().get_db().session
        obj = await db_session.exec(select(Worker).
                                    where(Worker.phone == phone))

        return obj.scalar_one_or_none()

    async def get_phone_exclude_me(
            self, *, phone: str,
            db_session: AsyncSession | None = None,
            worker_id: str) -> list[Worker] | None:
        db_session = db_session or super().get_db().session
        objs = await db_session.exec(
            select(Worker).
            where(
                and_(
                    Worker.phone == phone,
                    Worker.id != worker_id)))

        return objs.scalars().all()

    async def get_email_exclude_me(
            self, *, email: str,
            db_session: AsyncSession | None = None,
            worker_id: str) -> list[Worker] | None:
        db_session = db_session or super().get_db().session
        objs = await db_session.exec(
            select(Worker)
            .where(
                and_(
                    Worker.email == email,
                    Worker.id != worker_id)))

        return objs.scalars().all()

    async def create(
            self, *, obj_in: WorkerCreateUpdateSch,
            worker_id: str | None = None,
            db_session: AsyncSession | None = None,
    ) -> Worker:
        db_session = db_session or super().get_db().session

        db_obj = self.model.model_validate(obj_in)  # type: ignore

        db_obj.created_by_id = worker_id
        db_obj.updated_by_id = worker_id

        ls_role: list[Role] | None = await crud.role.get_highest_role_per_group_from_list_id(list_role_id=obj_in.roles_id)

        db_obj.roles = ls_role

        response_exist: dict = await OauthService().check_user_by_email_or_phone(email=obj_in.email, phone=obj_in.phone)

        letters = string.ascii_letters
        password = ''.join(random.choice(letters) for _ in range(8))

        oauth_response: OauthUser | None = None

        if 'detail' in response_exist:
            first_name, *last_name = str(obj_in.name).split(' ', 1)
            data = {
                'email': obj_in.email,
                'mobile_no': obj_in.phone.replace('+', '') if obj_in.phone is not None else None,
                'first_name': first_name,
                'last_name': ''.join(last_name),
                'email_verified': False,
                'mobile_verified': False,
                'password': password,
                'roles': [settings.OAUTH_ROLE]
            }
            try:
                oauth_response = await OauthService().register_user_oauth(body=data)
            except Exception as e:
                await db_session.rollback()

                raise e

        elif (response_exist['mobile'] == response_exist['email'] and response_exist['email'] is not None) or (response_exist['email'] is not None and response_exist['mobile'] is None and response_exist['email']['mobile_no'] is None):
            data = response_exist['email']
            data['mobile_no'] = obj_in.phone.replace('+', '') if obj_in.phone is not None else None
            id = data.pop('id')
            data['password'] = password
            _ = [data.pop(e) for e in ['avatar', 'full_name']]
            _ = data['roles'].append(settings.OAUTH_ROLE) if settings.OAUTH_ROLE not in data['roles'] else data['roles']

            try:
                oauth_response = await OauthService().update_user_oauth(body=data, id=id)
            except Exception as e:
                await db_session.rollback()

                raise e
        else:
            await db_session.rollback()

            if response_exist['mobile'] is not None and response_exist['mobile']['email'] != obj_in.email:
                raise HTTPException(status_code=409,
                                    detail='Mobile Number already register in our subsystem with another email address')
            elif response_exist['email'] is not None and change_phone_format(response_exist['email']['mobile_no']) != obj_in.phone:
                raise HTTPException(
                    status_code=409, detail='Email already register in our subsystem with other mobile number')

            raise HTTPException(status_code=400, detail='Something wrong. Please contact developer.')

        db_obj.oauth_id = oauth_response.id

        db_session.add(db_obj)

        await db_session.commit()
        await db_session.refresh(db_obj)
        return db_obj

    async def update(
            self, *, obj_current: Worker,
            obj_new: WorkerCreateUpdateSch,
            db_session: AsyncSession | None = None,
            worker_id: str | None = None) -> Worker:
        db_session = db_session or super().get_db().session
        obj_current = await super().update(obj_current=obj_current, obj_new=obj_new,
                                           db_session=db_session, updated_by=worker_id, with_commit=False)

        ls_role: list[Role] | None = await crud.role.get_highest_role_per_group_from_list_id(list_role_id=obj_new.roles_id)

        obj_current.roles = []
        obj_current.roles = ls_role

        response_exist = await OauthService().check_user_by_email_or_phone(email=obj_new.email, phone=obj_new.phone)

        letters = string.ascii_letters
        password = ''.join(random.choice(letters) for _ in range(8))

        oauth_response: OauthUser | None = None

        if obj_current.oauth_id is not None:
            response_exist = await OauthService().get_user_by_id(oauth_id=str(obj_current.oauth_id))

            if 'detail' in response_exist:
                raise HTTPException(status_code=409, detail='Something wrong, please contact developer')

            response_exist = await OauthService().check_user_by_email_or_phone(email=obj_current.email, phone=obj_current.phone)

            if (response_exist['mobile'] == response_exist['email'] and response_exist['email'] is not None) or (response_exist['email'] is not None and response_exist['mobile'] is None and (response_exist['email']['mobile_no'] is None or response_exist['email']['id'] == str(obj_current.oauth_id))) or (obj_current.phone is not None and response_exist['mobile'] is not None and response_exist['email'] is None and response_exist['mobile']['id'] == str(obj_current.oauth_id)):
                data = response_exist['email'] if response_exist['email'] is not None else response_exist['mobile']
                data['mobile_no'] = obj_current.phone.replace('+', '') if obj_current.phone is not None else None
                id = data.pop('id')
                data['password'] = password
                _ = [data.pop(e) for e in ['avatar', 'full_name']]
                _ = data['roles'].append(
                    settings.OAUTH_ROLE) if settings.OAUTH_ROLE not in data['roles'] else data['roles']

                try:
                    oauth_response = await OauthService().update_user_oauth(body=data, id=id)
                except Exception as e:
                    await db_session.rollback()

                    raise e
            else:
                await db_session.rollback()

                if response_exist['mobile'] is not None and response_exist['mobile']['email'] != obj_new.email:
                    raise HTTPException(
                        status_code=409, detail='Mobile Number already register in our subsystem with another email address')
                elif response_exist['email'] is not None and change_phone_format(response_exist['email']['mobile_no']) != obj_new.phone:
                    raise HTTPException(
                        status_code=409, detail='Email already register in our subsystem with other mobile number')

                raise HTTPException(status_code=409, detail='Something wrong, please contact developer')
        else:
            response_exist = await OauthService().check_user_by_email_or_phone(email=obj_current.email, phone=obj_current.phone)
            if 'detail' in response_exist:
                first_name, *last_name = str(obj_current.name).split(' ', 1)
                data = {
                    'email': obj_current.email,
                    'mobile_no': obj_current.phone.replace('+', '') if obj_current.phone is not None else None,
                    'first_name': first_name,
                    'last_name': ''.join(last_name),
                    'email_verified': False,
                    'mobile_verified': False,
                    'password': password,
                    'roles': [settings.OAUTH_ROLE]
                }

                try:
                    oauth_response = await OauthService().register_user_oauth(body=data)
                except Exception as e:
                    await db_session.rollback()

                    raise e
            elif (response_exist['mobile'] == response_exist['email'] and response_exist['email'] is not None) or (response_exist['email'] is not None and response_exist['mobile'] is None and (response_exist['email']['mobile_no'] is None or response_exist['email']['id'] == str(obj_current.id))):
                data = response_exist['email']
                data['mobile_no'] = obj_current.phone.replace(
                    '+', '') if obj_current.phone is not None else data['mobile_no']
                id = data.pop('id')
                data['password'] = password
                _ = [data.pop(e) for e in ['avatar', 'full_name']]
                _ = data['roles'].append(
                    settings.OAUTH_ROLE) if settings.OAUTH_ROLE not in data['roles'] else data['roles']

                try:
                    oauth_response = await OauthService().update_user_oauth(body=data, id=id)
                except Exception as e:
                    await db_session.rollback()

                    raise e
            else:
                await db_session.rollback()

                if response_exist['mobile'] is not None and response_exist['mobile']['email'] != obj_new.email:
                    raise HTTPException(status_code=409,
                                        detail='Mobile Number already register in our subsystem with another email address')
                elif response_exist['email'] is not None and change_phone_format(response_exist['email']['mobile_no']) != obj_new.phone:
                    raise HTTPException(
                        status_code=409, detail='Email already register in our subsystem with other mobile number')

                raise HTTPException(detail={'detail': 'Something wrong. Please contact developer.'}, status_code=409)

        obj_current.oauth_id = oauth_response.id

        db_session.add(obj_current)

        await db_session.commit()
        await db_session.refresh(obj_current)
        return obj_current

    async def remove(
            self, *, id: str,
            db_session: AsyncSession | None = None,
            worker_id: str | None = None) -> Worker:
        db_session = db_session or super().get_db().session
        response = await db_session.exec(
            select(self.model).where(self.model.id == id)
        )
        obj = response.scalar_one()
        obj.is_active = False
        obj.updated_by_id = worker_id
        db_session.add(obj)

        await db_session.commit()
        await db_session.refresh(obj)
        return obj

    async def get_active_worker_by_oauth_id(self, oauth_id: str):
        db_session = super().get_db().session

        try:
            db_obj = await db_session.exec(
                select(Worker)
                .where(
                    and_(
                        Worker.oauth_id == oauth_id,
                        Worker.is_active == True
                    )))
            worker_obj = db_obj.scalar_one_or_none()
        except Exception as ex:
            await db_session.rollback()
            raise HTTPException(
                status_code=409,
                detail=str(ex),
            )
        if worker_obj:
            return worker_obj
        else:
            raise HTTPException(status_code=401, detail='Worker Tidak Aktif')

    async def get_active_worker(self, request: Request) -> Worker:
        return await self.get_active_worker_by_oauth_id(oauth_id=request.state.access_token.user_id)


worker = CRUDWorker(Worker)
