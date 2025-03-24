import io
from minio import Minio
from minio.error import S3Error
from app.config import minio_settings as settings

minio_client = Minio(
    endpoint=settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ROOT_USER,
    secret_key=settings.MINIO_ROOT_PASSWORD,
    secure=False,
)


def file_exists_in_minio(file_hash: str) -> bool:
    """Проверяет, существует ли файл с данным хешем в MinIO."""
    try:
        minio_client.stat_object(settings.MINIO_BUCKET_NAME, file_hash)
        return True
    except S3Error:
        return False


def ensure_bucket_exists():
    """Создает бакет, если его нет."""
    try:
        if not minio_client.bucket_exists(settings.MINIO_BUCKET_NAME):
            minio_client.make_bucket(settings.MINIO_BUCKET_NAME)
    except S3Error as e:
        print(f"Ошибка MinIO: {e}")


def upload_to_minio(file_data: bytes, file_hash: str):
    """Загружает файл в MinIO."""
    ensure_bucket_exists()

    file_stream = io.BytesIO(file_data)  # Обернем в поток

    minio_client.put_object(
        bucket_name=settings.MINIO_BUCKET_NAME,
        object_name=file_hash,
        data=file_stream,
        length=len(file_data),
        content_type="application/zip",
    )
    return True


def download_from_minio(file_hash: str) -> bytes | None:
    """Загружает файл из MinIO и возвращает его в виде байтов."""
    try:
        response = minio_client.get_object(
            bucket_name=settings.MINIO_BUCKET_NAME,
            object_name=file_hash,
        )
        file_data = response.read()
        return file_data
    except Exception as e:
        print(f"Ошибка загрузки файла из MinIO: {e}")
        return None


def delete_from_minio(file_hash: str) -> bool:
    """Удаляет файл из MinIO."""
    try:
        minio_client.remove_object(settings.MINIO_BUCKET_NAME, file_hash)
        return True
    except S3Error as e:
        print(f"Ошибка удаления файла из MinIO: {e}")
        return False
