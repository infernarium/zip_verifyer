import time
import random


def mock_external_api_coverage(file: bytes):
    """
    Эмулирует запрос к первой системе (анализ кода).
    Args:
        task_id (str): Идентификатор задачи.
    Returns:
        dict: Словарь с результатами анализа кода.
    Raises:
        Exception: Если произошла ошибка при эмуляции запроса.

    """
    if random.random() < 0.2:  # эмуляция ошибки
        raise Exception(f"Ошибка в mock_external_api_1")
    time.sleep(random.uniform(1, 10))
    return {
        "coverage": round(random.uniform(60, 90), 2),
        "bugs": {
            "total": random.randint(5, 20),
            "critical": random.randint(0, 5),
            "major": random.randint(0, 10),
            "minor": random.randint(0, 15),
        },
    }
