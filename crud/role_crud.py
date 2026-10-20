from fastapi_async_sqlalchemy import db
from sqlalchemy import and_, func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from crud.base_crud import CRUDBase
from models import Role
from schemas.role_schema import RoleCreateSch, RoleUpdateSch


class CRUDRole(CRUDBase[Role, RoleCreateSch, RoleUpdateSch]):
    async def get_highest_role_per_group_from_list_id(self, list_role_id: list[str], db_session: AsyncSession | None = None) -> list[Role] | None:
        db_session = db_session or db.session

        subquery = select(Role.group_number, func.max(Role.priority_in_group).label("priority_in_group"),
                          ).filter(Role.id.in_(list_role_id)).group_by(Role.group_number).subquery()

        query = select(Role).select_from(subquery).where(and_(Role.group_number == subquery.c.group_number,
                                                              Role.priority_in_group == subquery.c.priority_in_group))

        response = await db_session.exec(query)

        return response.scalars().all()


role = CRUDRole(Role)
