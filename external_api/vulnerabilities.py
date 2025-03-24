import time
import random


def mock_external_api_vulnerabilities(file: bytes):
    """
    Эмулирует запрос ко второй системе (проверка уязвимостей).
    Args:
        task_id (str): Идентификатор задачи.
    Returns:
        dict: Словарь с результатами проверки уязвимостей.
    """
    time.sleep(random.uniform(5, 10))
    return {
        "vulnerabilities": {
            "total": random.randint(5, 20),
            "critical": random.randint(0, 5),
            "major": random.randint(0, 10),
            "minor": random.randint(0, 15),
        },
    }
