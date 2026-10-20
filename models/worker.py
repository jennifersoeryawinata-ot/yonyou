from uuid import UUID

from pydantic import EmailStr
from sqlmodel import Field, Relationship

from models.base_model import BaseULIDModel, SQLModel


class WorkerRoleLink(SQLModel, table=True):
    worker_id: str | None = Field(default=None, foreign_key='worker.id', primary_key=True, max_length=26)
    role_id: str | None = Field(default=None, foreign_key='role.id', primary_key=True, max_length=26)


class RoleBase(SQLModel):
    name: str = Field(nullable=False, max_length=50)
    group_number: int = Field(nullable=False)
    priority_in_group: int = Field(nullable=False)


class RoleFullBase(RoleBase, BaseULIDModel):
    pass


class Role(RoleFullBase, table=True):
    pass


class WorkerBase(SQLModel):
    name: str = Field(nullable=False, max_length=100)
    phone: str | None = Field(nullable=True, max_length=18)
    email: EmailStr = Field(nullable=False)
    oauth_id: UUID | None = Field(nullable=True)
    is_active: bool = Field(default=True)


class WorkerFullBase(WorkerBase, BaseULIDModel):
    pass


class Worker(WorkerFullBase, table=True):
    roles: list['Role'] = Relationship(
        link_model=WorkerRoleLink,
        sa_relationship_kwargs={
            'lazy': 'select'
        }
    )

    @property
    def get_roles_name(self) -> list[str]:
        return_list = []
        for i in self.roles:
            return_list.append(i.name)
        return return_list

    @property
    def is_admin(self) -> bool:
        return True if "ADMIN" in self.get_roles_name or "SUPER_ADMIN" in self.get_roles_name else False

    @property
    def is_super_admin(self) -> bool:
        return True if "SUPER_ADMIN" in self.get_roles_name else False

    