from fastapi.encoders import jsonable_encoder
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from configs.config import settings
from typing import Dict, Any
import crud
import json
import datetime

class GCloudTaskService:
    TOKEN = settings.OAUTH2_TOKEN

    @property
    def _cloud_task_client(self):
        return tasks_v2.CloudTasksClient()

    def send_task(self, url, queue_name, http_method='POST', payload=None, in_seconds=settings.QUEUE_INSECONDS, task_name=None, token=None, *, with_oidc_token: bool = False, oidc_sa: str = None):
        # Construct the fully qualified queue name.
        parent = self._cloud_task_client.queue_path(
            settings.PROJECT_NAME, settings.QUEUE_LOCATION, queue=queue_name)

        # Construct the request body.
        task = {
            "http_request": {  # Specify the type of request.
                "http_method": http_method,
                "url": url,  # The full url path that the task will be sent to.
                "headers": {"Authorization": "Bearer " +  (self.TOKEN if token is None else token),
                "Content-Type": "application/json"}
            }
        }

        if with_oidc_token and oidc_sa is not None:
            task["http_request"]["oidc_token"] = {
                "service_account_email": oidc_sa,
                "audience": url
            }

        if payload is not None:
            if isinstance(payload, dict):
                # Convert dict to JSON string
                payload = json.dumps(payload)
                # specify http content-type to application/json
                task["http_request"]["headers"] = {
                    "Authorization": "Bearer " +  (self.TOKEN if token is None else token), 
                    "Content-Type": "application/json"}
            # The API expects a payload of type bytes.
            converted_payload = payload.encode()

            # Add the payload to the request.
            task["http_request"]["body"] = converted_payload

        if in_seconds is not None:
            # Convert "seconds from now" into an rfc3339 datetime string.
            d = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=in_seconds)

            # Create Timestamp protobuf.
            timestamp = timestamp_pb2.Timestamp()
            timestamp.FromDatetime(d)

            # Add the timestamp to the tasks.
            task["schedule_time"] = timestamp

        if task_name is not None:
            # Add the name to tasks.
            task["name"] = self._cloud_task_client.task_path(
            settings.PROJECT_NAME, settings.QUEUE_LOCATION, queue_name, task_name)

        # Use the client to build and send the task.
        response = self._cloud_task_client.create_task(request={"parent": parent, "task": task})

        print("Created task {}".format(response.name))
        return response