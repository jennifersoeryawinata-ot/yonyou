from fastapi import APIRouter, Depends, Query, status
from fastapi_pagination import Params
from sqlalchemy import and_
from sqlmodel import or_, select

import crud
import deps
from configs.permission import Permission
from models import Role, Worker
from schemas.response_schema import (DeleteResponseSchema, GetResponseBaseSchema,
                                  GetResponsePaginatedSchema, PostResponseSchema,
                                  PutResponseSchema, create_response)
from schemas.worker_schema import (ClientInquiryWorkerSch, WorkerByIdSch,
                                WorkerCreateUpdateSch, WorkerSch)
from services.oauth_service import OauthService

router = APIRouter()


@router.get("", response_model=GetResponsePaginatedSchema[WorkerSch])
async def get(
        params: Params = Depends(),
        search: str = Query(description='Search worker by name, email, phone', default=None),
        current_worker: Worker = Depends(crud.worker.get_active_worker),
):
    query = select(Worker)

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

    if search:
        query = query.filter(
            or_(
                Worker.name.contains(search),
                Worker.email.contains(search),
                Worker.phone.contains(search)
            )
        ).distinct()

    objs = await crud.worker.get_multi_paginated_ordered(params=params, query=query, order_by=['name'])
    return create_response(data=objs)

@router.get('/by-token', response_model=GetResponseBaseSchema[WorkerByIdSch])
async def get_worker_by_token_data(
    current_worker: Worker = Depends(crud.worker.get_active_worker)
):
    return create_response(current_worker)


@router.get("/{id}", response_model=GetResponseBaseSchema[WorkerByIdSch])
async def get_by_id(
    worker: Worker = Depends(deps.get_worker_by_id),
):
    return create_response(data=worker)


@router.post(
    "",
    response_model=PostResponseSchema[WorkerByIdSch],
    status_code=status.HTTP_201_CREATED,
)
async def create(
    sch: WorkerCreateUpdateSch,
    current_worker: Worker = Depends(crud.worker.get_active_worker),
    _: Worker | None = Depends(deps.worker_phone_email_deps)
):
    new_obj = await crud.worker.create(obj_in=sch, worker_id=current_worker.id)

    return create_response(data=new_obj)


@router.put("/{id}", response_model=PutResponseSchema[WorkerByIdSch])
async def update(
    sch: WorkerCreateUpdateSch,
    worker: Worker = Depends(deps.get_worker_by_id),
    current_worker: Worker = Depends(crud.worker.get_active_worker),
    _: Worker | None = Depends(deps.worker_phone_email_deps)
):
    obj_updated = await crud.worker.update(obj_current=worker, obj_new=sch, worker_id=current_worker.id)

    return create_response(data=obj_updated)


@router.delete("/{id}", response_model=DeleteResponseSchema[WorkerByIdSch])
async def delete(
    worker: Worker = Depends(deps.get_worker_by_id),
    current_worker: Worker = Depends(crud.worker.get_active_worker)
):
    obj_current = await crud.worker.remove(id=worker.id, worker_id=current_worker.id)
    return create_response(data=obj_current)


router_client = APIRouter()


@router_client.post("/inquiry", response_model=GetResponseBaseSchema[WorkerByIdSch], dependencies=[Depends(Permission().is_allowed_client_fetch_worker)])
async def inquiry_worker(sch: ClientInquiryWorkerSch):
    at = await OauthService().check_token(token=sch.token)

    worker: Worker | None = await crud.worker.get_active_worker_by_oauth_id(oauth_id=at.user_id)

    return create_response(data=worker)
