# Publish to Pub/Sub
import base64
import json

from google.cloud import pubsub_v1
from configs.config import settings
from fastapi import Request
from fastapi.encoders import jsonable_encoder

class PubSubService:
    __projectId:str
    def __init__(self, projectId:str=settings.PROJECT_ID):
        self.__projectId = projectId
    async def generatePublisherMessage(self, request: Request, base64Str: str|None):
        base64_data = ""
        if base64Str and base64Str != "" :
            #decodedata =  json.loads(base64Str)
            base64_data =  base64Str #decodedata['message']['data']
        else:
            data = await request.body()
            print(data.decode('utf-8'), flush=True)
            decodedata =  json.loads((data.decode('utf-8')))    
            base64_data = decodedata['message']['data']
        decoded_data = base64.b64decode(base64_data).decode('utf-8')
        message_object = json.loads(decoded_data)
        # [message_object.pop(key) for key in ['deleted_date']]
        print(message_object, flush=True)
        return  message_object
    
    def publish_to_pubsub(self, topic_name, message, action):
        try:
            if isinstance(message, dict):
                message_dict = message
            else:
                message_dict = message.dict()
                
            message_dict['action'] = action
            publisher = pubsub_v1.PublisherClient()
            topic_path = publisher.topic_path(self.__projectId, topic_name + settings.PUBSUB_SUFFIX)
            message_data = json.dumps(message_dict, indent=4, sort_keys=True, default=str).encode("utf-8")
            future = publisher.publish(topic_path, data=message_data)
            # print(f"Published message ID: {future.result()}")
            
        except Exception as e:
            print(e)
            
pubsub_service = PubSubService()