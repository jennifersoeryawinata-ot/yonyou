import re

from pydantic import field_validator
from sqlmodel import SQLModel

from models import Role, WorkerBase, WorkerFullBase


class WorkerSch(WorkerFullBase):
    pass


class WorkerByIdSch(WorkerSch):
    roles: list[Role]


class WorkerCreateUpdateSch(WorkerBase):
    roles_id: list[str]

    @field_validator('phone')
    def validate_phone(cls, phone):
        if phone is None or phone == '':
            return None
        else:
            phone = re.sub('[^0-9 +]', '', phone)

        if phone.startswith('0'):
            phone = '62'+phone[1:]
        elif phone.startswith('8'):
            phone = '62'+phone

        if not phone.startswith('+'):
            phone = '+'+phone

        return phone


class ClientInquiryWorkerSch(SQLModel):
    token: str
