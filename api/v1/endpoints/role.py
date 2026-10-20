from fastapi import APIRouter, Depends, exceptions
from fastapi_pagination import Params
from sqlalchemy import select, text

import crud
from models import Role, Worker
from schemas.response_schema import (GetResponseBaseSchema, GetResponsePaginatedSchema,
                                  create_response)
from schemas.role_schema import RoleSch

router = APIRouter()


@router.get("", response_model=GetResponsePaginatedSchema[RoleSch])
async def get(
    param: Params = Depends(),
    current_worker: Worker = Depends(crud.worker.get_active_worker)
):
    query = select(Role)
    if current_worker.is_admin and current_worker.is_super_admin == False:
        query = query.filter(Role.name == 'USER')
    elif current_worker.is_super_admin == False:
        query = query.filter(Role.id == '')

    objs = await crud.role.get_multi_paginated_ordered(params=param, order_by=['group_number', 'priority_in_group', 'name'], query=query)
    

    return create_response(data=objs)


@router.get("/no-page", response_model=GetResponseBaseSchema[list[RoleSch]])
async def get_no_page(
    current_worker: Worker = Depends(crud.worker.get_active_worker)
):
    query = select(Role)
    if current_worker.is_admin and current_worker.is_super_admin == False:
        query = query.filter(Role.name == 'USER')
    elif current_worker.is_super_admin == False:
        raise exceptions.HTTPException(status_code=401, detail='Unauthorized')

    objs = await crud.role.get_all_ordered(order_by=['group_number', 'priority_in_group', 'name'], query=query)
    return create_response(data=objs)
