# Команда запуска: celery -A app.services.celery worker -l info -P eventlet
import json
from typing import Optional

from celery import shared_task  # type: ignore
from celery.utils.log import get_task_logger  # type: ignore
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, redis_client_sync
from app.models.task_result import TaskResult, TaskStatusEnum
from app.services.minio_client import download_from_minio

from external_api.coverage import mock_external_api_coverage
from external_api.smells import mock_external_api_smells
from external_api.vulnerabilities import mock_external_api_vulnerabilities

from celery import Celery
from app.config import celery_settings as settings


logger = get_task_logger(__name__)

celery_app = Celery("tasks", broker=settings.CELERY_BROKER_URL)
celery_app.autodiscover_tasks(["app.services"])

celery_app.conf.task_routes = {
    "app.services.celery.*": {"queue": "zip_queue"},
}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    name="process_zip_task",
)
def process_zip_task(self, task_id: str):
    """
    Фоновая обработка ZIP-архива с загрузкой из MinIO и запросами к сторонним API.

    Args:
        task_id (str): Идентификатор задачи.

    Returns:
        dict: Результаты обработки.

    Raises:
        Exception: Если произошла ошибка при обработке.
    """
    db: Session = SessionLocal()

    try:
        task = db.query(TaskResult).filter(TaskResult.task_id == task_id).first()
        if task is None:
            logger.error(f"Задача [{task_id}] не найдена в БД")
            return

        # Теперь `mypy` понимает, что `task` не `None`
        task.status = TaskStatusEnum.IN_PROGRESS
        db.commit()
        update_cache(task_id, task.status, None)

        logger.info(f"Начинаем загрузку ZIP-архива [{task_id}] из MinIO")

        # Загружаем архив из MinIO
        local_zip_path = download_from_minio(task_id)
        if not local_zip_path:
            raise Exception(f"Ошибка загрузки [{task_id}] из MinIO")

        logger.info(f"Архив успешно загружен")
        logger.info(f"Передача архива во внешние API")

        # Запросы к внешним API
        api_1_result = mock_external_api_coverage(local_zip_path)
        api_2_result = mock_external_api_vulnerabilities(local_zip_path)
        api_3_result = mock_external_api_smells(local_zip_path)

        results = {
            "overall_coverage": api_1_result["coverage"],
            "bugs": api_1_result["bugs"],
            "vulnerabilities": api_2_result["vulnerabilities"],
            "code_smells": api_3_result["code_smells"],
        }

        # Обновляем статус на SUCCESS и сохраняем результаты
        task.status = TaskStatusEnum.SUCCESS
        task.results = results
        db.commit()

        update_cache(task_id, task.status, task.results)

        logger.info(f"Задача [{task_id}] успешно завершена")
        return results

    except Exception as e:
        logger.error(f"[{task_id}] Ошибка обработки: {e}")

        if task is None:
            return

        task.status = TaskStatusEnum.FAILED
        db.commit()
        update_cache(task_id, task.status, None)
        raise self.retry(exc=e)

    finally:
        db.close()


def update_cache(task_id: str, status: TaskStatusEnum, results: Optional[dict]):
    """
    Обновляет кэш Redis для задачи.
    """
    cache_data = {
        "status": status.value,
        "results": results if results is not None else None,
    }

    try:
        logger.info(f"Обновляем кэш в Redis: {task_id} -> {cache_data}")

        # Обновляем кэш
        redis_client_sync.setex(task_id, 300, json.dumps(cache_data))

    except Exception as e:
        logger.error(f"Ошибка при кэшировании задачи [{task_id}]: {e}")
