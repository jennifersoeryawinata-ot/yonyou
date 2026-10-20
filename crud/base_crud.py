from typing import Any, Dict, Generic, Type, TypeVar

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi_async_sqlalchemy import db
from fastapi_pagination import Page, Params
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel
from sqlalchemy import exc, func, select
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.sql.expression import Select

ModelType = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)
SchemaType = TypeVar("SchemaType", bound=BaseModel)
T = TypeVar("T", bound=SQLModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD object with default methods to Create, Read, Update, Delete (CRUD).
        **Parameters**
        * `model`: A SQLModel model class
        * `schema`: A Pydantic model (schema) class
        """
        self.model = model
        self.db = db

    def get_db(self):
        return self.db

    async def get(
        self, *, id: str, db_session: AsyncSession | None = None
    ) -> ModelType | None:
        db_session = db_session or db.session
        query = select(self.model).where(self.model.id == id)
        response = await db_session.exec(query)
        return response.scalar_one_or_none()

    async def get_by_ids(
        self,
        *,
        list_ids: list[str],
        db_session: AsyncSession | None = None,
    ) -> list[ModelType] | None:
        db_session = db_session or db.session
        response = await db_session.exec(
            select(self.model).where(self.model.id.in_(list_ids))
        )
        return response.scalars().all()

    async def exclude(
        self,
        *,
        list_ids: list[str],
        db_session: AsyncSession | None = None,
    ) -> list[ModelType] | None:
        db_session = db_session or db.session
        response = await db_session.exec(
            select(self.model).where(self.model.id.notin_(list_ids))
        )
        return response.scalars().all()

    async def get_count(
        self, db_session: AsyncSession | None = None
    ) -> ModelType | None:
        db_session = db_session or db.session
        response = await db_session.exec(
            select(func.count).select_from(select(self.model).subquery())
        )
        return response.scalar_one()

    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        query: T | Select[T] | None = None,
        db_session: AsyncSession | None = None,
    ) -> list[ModelType]:
        db_session = db_session or db.session
        if query is None:
            query = select(self.model).offset(skip).limit(limit).order_by(self.model.id)
        response = await db_session.exec(query)
        return response.scalars().all()

    async def get_multi_paginated(
        self,
        *,
        params: Params | None = Params(),
        query: T | Select[T] | None = None,
        db_session: AsyncSession | None = None,
    ) -> Page[ModelType]:
        db_session = db_session or db.session
        if query is None:
            query = select(self.model)
        return await paginate(db_session, query, params)

    async def get_multi_paginated_ordered(
        self,
        *,
        params: Params | None = Params(),
        order_by: list[str] | None = [],
        query: T | Select[T] | None = None,
        db_session: AsyncSession | None = None,
    ) -> Page[ModelType]:
        db_session = db_session or db.session

        columns = self.model.__table__.columns

        if query is None:
            query = select(self.model)

        for order in order_by:
            if order.replace('-', '') not in columns:
                raise HTTPException(
                    status_code=404,
                    detail='order_by not in table'
                )

            if order.startswith('-'):
                order = order.replace('-', '')
                query = query.order_by(columns[order].desc())
            else:
                query = query.order_by(columns[order].asc())

        return await paginate(db_session, query, params)

    async def get_multi_ordered(
        self,
        *,
        order_by: list[str] = [],
        query: T | Select[T] | None = None,
        skip: int = 0,
        limit: int = 100,
        db_session: AsyncSession | None = None,
    ) -> list[ModelType]:
        db_session = db_session or db.session

        columns = self.model.__table__.columns

        if query is None:
            query = select(self.model)

        query = query.offset(skip).limit(limit)

        for order in order_by:
            if order.replace('-', '') not in columns:
                raise HTTPException(
                    status_code=404,
                    detail='order_by not in table'
                )

            if order.startswith('-'):
                order = order.replace('-', '')
                query = query.order_by(columns[order].desc())
            else:
                query = query.order_by(columns[order].asc())

        response = await db_session.exec(query)
        return response.scalars().all()

    async def get_all_ordered(
        self,
        *,
        query: T | Select[T] | None = None,
        order_by: list[str] = [],
        db_session: AsyncSession | None = None,
    ) -> list[ModelType]:
        db_session = db_session or db.session

        columns = self.model.__table__.columns

        if query is None:
            query = select(self.model)

        for order in order_by:
            if order.replace('-', '') not in columns:
                raise HTTPException(
                    status_code=404,
                    detail='order_by not in table'
                )

            if order.startswith('-'):
                order = order.replace('-', '')
                query = query.order_by(columns[order].desc())
            else:
                query = query.order_by(columns[order].asc())

        response = await db_session.exec(query)
        return response.scalars().all()

    async def create(
        self,
        *,
        obj_in: CreateSchemaType | ModelType,
        created_by: str | None = None,
        db_session: AsyncSession | None = None,
        with_commit: bool | None = True,
    ) -> ModelType:
        db_session = db_session or db.session
        db_obj = self.model.model_validate(obj_in)  # type: ignore

        if created_by:
            db_obj.created_by = created_by
            db_obj.updated_by = created_by

        try:
            db_session.add(db_obj)
            if with_commit:
                await db_session.commit()
        except exc.IntegrityError:
            await db_session.rollback()
            raise HTTPException(
                status_code=409,
                detail="Resource already exists",
            )
        if with_commit:
            await db_session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        *,
        obj_current: ModelType,
        obj_new: UpdateSchemaType | Dict[str, Any] | ModelType,
        db_session: AsyncSession | None = None,
        updated_by: str | None = None,
        with_commit: bool | None = True,
    ) -> ModelType:
        db_session = db_session or db.session
        obj_data = jsonable_encoder(obj_current)

        if isinstance(obj_new, dict):
            update_data = obj_new
        else:
            update_data = obj_new.model_dump(
                exclude_unset=True
            )  # This tells Pydantic to not include the values that were not sent

        for field in obj_data:
            if field in update_data:
                setattr(obj_current, field, update_data[field])

        if updated_by:
            obj_current.updated_by = updated_by

        db_session.add(obj_current)
        if with_commit:
            await db_session.commit()
            await db_session.refresh(obj_current)
        return obj_current

    async def remove(
        self, *, id: str, db_session: AsyncSession | None = None
    ) -> ModelType:
        db_session = db_session or db.session
        response = await db_session.exec(
            select(self.model).where(self.model.id == id)
        )
        obj = response.scalar_one()
        await db_session.delete(obj)
        await db_session.commit()
        return obj
