from typing import Annotated

from fastapi import Depends, Path

import crud
from models import Worker
from schemas.worker_schema import WorkerCreateUpdateSch
# from utils.exceptions.common_exception import (EmailExistException,
#                                                IdNotFoundException,
#                                                PhoneExistException)


async def worker_phone_email_deps(
        sch: WorkerCreateUpdateSch,
        id: str | None = None,
):
    if (sch.phone is not None):
        if (id is not None):
            worker: Worker | None = await crud.worker.get_phone_exclude_me(worker_id=id, phone=sch.phone)
        else:
            worker: Worker | None = await crud.worker.get_by_phone(phone=sch.phone)

        # if worker:
        #     raise PhoneExistException(Worker, phone=sch.phone)

    if id is not None:
        worker: Worker | None = await crud.worker.get_email_exclude_me(worker_id=id, email=sch.email)
    else:
        worker: Worker | None = await crud.worker.get_by_email(email=sch.email)

    # if worker:
    #     raise EmailExistException(Worker, email=sch.email)


async def get_worker_by_id(
    id: Annotated[str, Path(title="The ULID id of the role")],
    current_worker: Worker = Depends(crud.worker.get_active_worker),
) -> Worker:
    worker: Worker | None = await crud.worker.get(id=id, current_worker=current_worker)
    # if not worker:
    #     raise IdNotFoundException(Worker, id=id)
    return worker
