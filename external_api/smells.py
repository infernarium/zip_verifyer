import time
import random


def mock_external_api_smells(file: bytes):
    """
    Эмулирует запрос к третьей системе (запахи кода).
    Args:
        task_id (str): Идентификатор задачи.
    Returns:
        dict: Словарь с результатами проверки code smells.
    """
    time.sleep(random.uniform(1, 5))
    return {
        "code_smells": {
            "total": random.randint(5, 20),
            "critical": random.randint(0, 5),
            "major": random.randint(0, 10),
            "minor": random.randint(0, 15),
        },
    }
