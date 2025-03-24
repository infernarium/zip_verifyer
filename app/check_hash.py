import hashlib
from fastapi import UploadFile


def calculate_file_hash(file: UploadFile) -> str:
    """Вычисляет SHA-256 хеш файла"""
    hasher = hashlib.sha256()
    file.file.seek(0)
    while chunk := file.file.read(4096):
        hasher.update(chunk)
    file.file.seek(0)
    return hasher.hexdigest()
