import datetime
import io
import base64
from typing import TypeVar, Union
from fastapi import UploadFile
from sqlmodel import SQLModel
from google.auth import default
from google.auth.impersonated_credentials import Credentials as ImpersonatedCredentials
from google.cloud import storage
from google.api_core.exceptions import NotFound
from ulid import ULID
from configs.config import settings

ModelType = TypeVar("ModelType", bound=SQLModel)

class GCloudStorageService:
    def __init__(self, bucketname: str = settings.BUCKET_NAME):
        # ADC akan otomatis mendeteksi project & kredensial dari environment
        source_credentials, project = default()
        sa_email = settings.SERVICE_ACCOUNT_BUCKET

        impersonated_credentials = ImpersonatedCredentials(
            source_credentials=source_credentials,
            target_principal=sa_email,
            target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )

        gcs_client = storage.Client(credentials=impersonated_credentials, project=project)

        self.client = gcs_client
        self.bucket = self.client.bucket(bucketname)
        self.folder = settings.FOLDER

    @staticmethod
    def path_and_rename(
        *,
        model_type: ModelType | None = None,
        upload_file: Union[UploadFile, bytes, io.BytesIO],
        folder: str | None = None,
        sub_folder: str | None = None,
        filename: str | None = None
    ) -> str:
        # Perbaikan penamaan folder default dari 'unknow/' ke 'unknown/'
        if folder:
            upload_to = f'{folder}/{sub_folder}/' if sub_folder else f'{folder}/'
        else:
            upload_to = 'unknown/'
        
        # Ekstraksi ekstensi file dengan aman
        if isinstance(upload_file, (bytes, io.BytesIO)):
            ext = filename.split('.')[-1] if filename else 'bin'
        else:
            ext = upload_file.filename.split('.')[-1] if upload_file.filename else 'bin'
        
        if not filename:
            if model_type and getattr(model_type, 'id', None):
                filename = f'{model_type.id}.{ext}'
            else:
                filename = f'{str(ULID())}.{ext}'

        return upload_to + filename

    def upload(self, filename: str, file):
        blob = self.bucket.blob(filename)
        blob.upload_from_file(file.file)

    def upload_file(
        self, 
        file: UploadFile, 
        obj_current: ModelType | None = None, 
        folder: str | None = None, 
        sub_folder: str | None = None, 
        content_type: str | None = None, 
        filename: str | None = None
    ) -> str:
        file_path = self.path_and_rename(
            model_type=obj_current, upload_file=file, folder=folder, sub_folder=sub_folder, filename=filename
        )
        blob = self.bucket.blob(file_path)
        blob.upload_from_file(file_obj=file.file, content_type=content_type)
        return file_path

    def upload_from_bytes(self, filename: str, file: bytes):
        blob = self.bucket.blob(filename)
        blob.upload_from_file(io.BytesIO(file))
    
    def upload_file_from_bytes(
        self, 
        file_bytes: Union[bytes, io.BytesIO, UploadFile], 
        filename: str, 
        content_type: str, 
        obj_current: ModelType | None = None, 
        folder: str | None = None, 
        sub_folder: str | None = None
    ) -> str:
        file_path = self.path_and_rename(
            upload_file=file_bytes, model_type=obj_current, folder=folder, sub_folder=sub_folder, filename=filename
        )
        blob = self.bucket.blob(file_path)
        
        # Standarisasi input menjadi BytesIO stream
        if isinstance(file_bytes, io.BytesIO):
            file_stream = io.BytesIO(file_bytes.getvalue())
        elif isinstance(file_bytes, UploadFile):
            # Karena ini fungsi sinkronus, membaca file_bytes (UploadFile) menggunakan .file.read()
            file_stream = io.BytesIO(file_bytes.file.read())
        else:
            file_stream = io.BytesIO(file_bytes)
            
        blob.upload_from_file(file_obj=file_stream, content_type=content_type)
        file_stream.close()
        return file_path
    
    def delete_blob(self, blob_name: str) -> None:
        # if blob_name is not None:
        #     blob = self.bucket.blob(blob_name)
        #     blob.delete()

        blob = self.bucket.blob(blob_name)

        try:
            blob.delete()
        except NotFound:
            raise FileNotFoundError(f"Blob '{blob_name}' not found or has been deleted.")

    def get_signed_url(self, filename: str, minutes: int = 15) -> str:
        """
        Membuat Signed URL v4 menggunakan ADC.
        Pastikan Service Account memiliki role 'Service Account Token Creator'.
        """

        blob = self.bucket.blob(filename)

        url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=minutes),
            method="GET",
            service_account_email=settings.SERVICE_ACCOUNT_BUCKET,
        )

        return url
    
    def get_url(self, filename: str)-> str:
        blob = self.bucket.blob(filename)
        blob.make_public()
        return self.bucket.blob(filename).public_url

    def get_base64_data(self, filename: str) -> str:
        blob = self.bucket.blob(filename)
        file_content = blob.download_as_string()
        return base64.b64encode(file_content).decode("utf-8")

    def get_string_data(self, filename: str) -> str:
        blob = self.bucket.blob(filename)
        return blob.download_as_string().decode("utf-8")

    def get_bytes_data(self, filename: str, file_path: str) -> bytes:
        # Memastikan slash antar path tergabung dengan benar
        full_path = f"{file_path.rstrip('/')}/{filename.lstrip('/')}"
        blob = self.bucket.blob(full_path)
        return blob.download_as_bytes()

# Inisialisasi singleton instance
gCloudStorage = GCloudStorageService()