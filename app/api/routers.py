import json

from fastapi import APIRouter, UploadFile, HTTPException, Depends
from pydantic import ValidationError
from app.api.schemas import UploadResponse, ResultsResponse, TestResults
from app.models.task_result import TaskResult, TaskStatusEnum
from app.services.minio_client import (
    delete_from_minio,
    upload_to_minio,
    file_exists_in_minio,
)
from app.services.celery import process_zip_task
from app.db.session import get_db, redis_client_async
from app.check_hash import calculate_file_hash
from sqlalchemy import text
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_zip(file: UploadFile, db: AsyncSession = Depends(get_db)):
    """
    Загрузка ZIP-архива на сервер.
    Args:
        file (UploadFile): ZIP-архив для загрузки.
        db (Session): Сессия базы данных.
    Returns:
        UploadResponse: Словарь с идентификатором задачи.
    Raises:
        HTTPException: Если файл не является ZIP-архивом, уже загружен или произошла ошибка при загрузке.
    """
    if (not file.filename) or (not file.filename.endswith(".zip")):
        raise HTTPException(status_code=400, detail="Только ZIP-архивы разрешены")

    file_data = await file.read()
    file_hash = calculate_file_hash(file)

    if file_exists_in_minio(file_hash):
        raise HTTPException(status_code=409, detail="Файл уже загружен")

    upload_result = upload_to_minio(file_data, file_hash)

    if not upload_result:
        raise HTTPException(status_code=500, detail="Ошибка при загрузке файла")

    task = TaskResult(task_id=file_hash, status=TaskStatusEnum.PENDING)

    try:
        db.add(task)
        await db.commit()
    except Exception as e:
        delete_from_minio(task.task_id)
        await db.rollback()
        raise HTTPException(status_code=500, detail="Ошибка при добавлении файла в бд")

    task_id = task.task_id

    # Отправляем задание в очередь Celery
    process_zip_task.apply_async(args=[task_id])

    return UploadResponse(task_id=task_id)


@router.get("/results/{task_id}", response_model=ResultsResponse)
async def get_results(task_id: str, db: AsyncSession = Depends(get_db)):
    """
    Возвращает результат проверки ZIP-архива из БД, используя кэширование в Redis.

    Args:
        task_id (str): Идентификатор задачи.
        db (AsyncSession): Асинхронная сессия базы данных.

    Returns:
        ResultsResponse: Объект с результатами проверки.

    Raises:
        HTTPException: Если задача не найдена или произошла ошибка при преобразовании JSON.
    """

    # Проверяем кэш Redis
    cache = await redis_client_async.get(task_id)

    if cache:
        try:
            cache_data = json.loads(cache)
            if cache_data["results"] is None:
                results = None
            else:
                results = TestResults(**cache_data["results"])
            return ResultsResponse(status=cache_data["status"], results=results)
        except (ValidationError, KeyError, json.JSONDecodeError) as e:
            raise HTTPException(status_code=500, detail=f"Ошибка кэша Redis: {e}")

    # Запрос к БД, если в кэше данных нет
    result = await db.execute(select(TaskResult).filter(TaskResult.task_id == task_id))
    task = result.scalars().first()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    results = None
    if task.results:
        try:
            results = TestResults(**task.results)
        except ValidationError as e:
            raise HTTPException(
                status_code=500, detail=f"Ошибка преобразования JSON: {e}"
            )

    # Кэшируем результат в Redis на 5 минут (300 секунд)
    cache_data = {
        "status": task.status.value,  # ✅ Преобразуем Enum в строку
        "results": task.results,
    }
    await redis_client_async.setex(task_id, 300, json.dumps(cache_data))

    return ResultsResponse(status=task.status, results=results)


@router.delete("/clear-database", response_model=dict)
async def clear_database(db: AsyncSession = Depends(get_db)):
    """
    Очищает базу данных и удаляет все файлы из MinIO.
    """
    try:
        result = await db.execute(select(TaskResult.task_id))
        task_ids = result.scalars().all()

        for task_id in task_ids:
            delete_from_minio(task_id)

        await db.execute(text("TRUNCATE TABLE task_results RESTART IDENTITY CASCADE"))
        await db.commit()

        return {"message": "База данных и файлы MinIO успешно очищены"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Ошибка при очистке: {str(e)}")
