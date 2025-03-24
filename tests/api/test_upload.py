import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch, Mock
from asgi_lifespan import LifespanManager
from app.main import app
from app.db.session import get_db


@pytest.mark.anyio("asyncio")
async def test_upload_without_file():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        response = await ac.post("/upload")
    assert response.status_code == 422


@pytest.mark.anyio
async def test_upload_correct_filetype():
    """Тест загрузи правильного ZIP-файла"""

    test_file = {"file": ("test.zip", b"Fake ZIP content", "application/zip")}

    mock_db_session = AsyncMock()

    async def override_get_db():
        yield mock_db_session

    mock_file_exists = Mock(return_value=False)
    mock_upload_to_minio = AsyncMock(return_value=True)
    mock_delete_from_minio = AsyncMock()
    mock_celery_task = AsyncMock()

    with (
        patch("app.api.routers.file_exists_in_minio", mock_file_exists),
        patch("app.api.routers.upload_to_minio", mock_upload_to_minio),
        patch("app.api.routers.delete_from_minio", mock_delete_from_minio),
        patch("app.api.routers.process_zip_task.apply_async", mock_celery_task),
    ):
        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post("/upload", files=test_file)

        assert response.status_code == 200
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_upload_incorrect_filetype():
    """Тест для загрузки файла некорректного типа (.txt)"""

    # Мок файла некорректного типа
    test_file = {"file": ("test.txt", b"Fake text content", "text/plain")}

    # Мок сессии базы данных
    mock_db_session = AsyncMock()

    # Асинхронная заглушка для получения сессии БД
    async def override_get_db():
        yield mock_db_session

    # Моки для работы с Minio
    mock_file_exists = Mock(return_value=False)
    mock_upload_to_minio = AsyncMock(return_value=True)
    mock_delete_from_minio = AsyncMock()
    mock_celery_task = AsyncMock()

    # Патчи для замены реальных функций на моки
    with (
        patch("app.api.routers.file_exists_in_minio", mock_file_exists),
        patch("app.api.routers.upload_to_minio", mock_upload_to_minio),
        patch("app.api.routers.delete_from_minio", mock_delete_from_minio),
        patch("app.api.routers.process_zip_task.apply_async", mock_celery_task),
    ):
        # Перегрузка зависимости для БД
        app.dependency_overrides[get_db] = override_get_db

        # Выполнение запроса с файлом
        async with AsyncClient(  # Мок файла некорректного типа
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.post("/upload", files=test_file)

        # Проверка, что файл с неправильным типом отклоняется
        assert (
            response.status_code == 400
        )  # Ожидаемый статус ошибки для неверного типа файла

        # Очистка зависимостей
        app.dependency_overrides.clear()


# @pytest.mark.anyio
# async def test_upload_file_retry():
#     """Тест для проверки повторной загрузки файла"""

#     # Мок файла (в данном случае файл типа .zip)
#     test_file = {"file": ("test.zip", b"Fake ZIP content", "application/zip")}

#     # Мок сессии базы данных
#     mock_db_session = AsyncMock()

#     # Асинхронная заглушка для получения сессии БД
#     async def override_get_db():
#         yield mock_db_session

#     # Моки для работы с Minio
#     mock_file_exists = Mock(side_effect=[False, True])
#     mock_upload_to_minio = AsyncMock(return_value=True)
#     mock_delete_from_minio = AsyncMock()
#     mock_celery_task = AsyncMock()

#     # Патчи для замены реальных функций на моки
#     with (
#         patch("app.api.routers.file_exists_in_minio", mock_file_exists),
#         patch("app.api.routers.upload_to_minio", mock_upload_to_minio),
#         patch("app.api.routers.delete_from_minio", mock_delete_from_minio),
#         patch("app.api.routers.process_zip_task.apply_async", mock_celery_task),
#     ):
#         # Перегрузка зависимости для БД
#         app.dependency_overrides[get_db] = override_get_db

#         # Первый запрос на загрузку файла (файл ещё не существует)
#         async with AsyncClient(
#             transport=ASGITransport(app=app), base_url="http://test"
#         ) as ac:
#             response = await ac.post("/upload", files=test_file)

#         # Проверка, что файл был загружен
#         assert response.status_code == 200
#         assert (
#             mock_upload_to_minio.call_count == 1
#         )  # Загрузка файла должна быть выполнена

#         # Второй запрос на загрузку того же файла (файл уже существует)
#         async with AsyncClient(
#             transport=ASGITransport(app=app), base_url="http://test"
#         ) as ac:
#             response = await ac.post("/upload", files=test_file)

#         # Проверка, что файл не был загружен повторно
#         assert (
#             response.status_code == 400
#         )  # Ожидаемый статус ошибки, если файл уже существует
#         assert (
#             mock_upload_to_minio.call_count == 1
#         )  # Загрузка файла должна произойти только один раз

#         # Очистка зависимостей
#         app.dependency_overrides.clear()


# @pytest.mark.anyio
# async def test_upload_different_files_with_same_name():
#     """Тест для загрузки различных файлов с одинаковым названием"""

#     # Мок разных файлов с одинаковым именем
#     test_file_1 = {"file": ("test.zip", b"Fake ZIP content 1", "application/zip")}
#     test_file_2 = {"file": ("test.zip", b"Fake ZIP content 2", "application/zip")}

#     # Мок сессии базы данных
#     mock_db_session = AsyncMock()

#     # Асинхронная заглушка для получения сессии БД
#     async def override_get_db():
#         yield mock_db_session

#     # Моки для работы с Minio
#     mock_file_exists = Mock(
#         side_effect=[False, True, False]
#     )  # Файл сначала не существует, потом существует, потом снова не существует
#     mock_upload_to_minio = AsyncMock(return_value=True)
#     mock_delete_from_minio = AsyncMock()
#     mock_celery_task = AsyncMock()

#     # Патчи для замены реальных функций на моки
#     with (
#         patch("app.api.routers.file_exists_in_minio", mock_file_exists),
#         patch("app.api.routers.upload_to_minio", mock_upload_to_minio),
#         patch("app.api.routers.delete_from_minio", mock_delete_from_minio),
#         patch("app.api.routers.process_zip_task.apply_async", mock_celery_task),
#     ):
#         # Перегрузка зависимости для БД
#         app.dependency_overrides[get_db] = override_get_db

#         # Загрузка первого файла
#         async with AsyncClient(
#             transport=ASGITransport(app=app), base_url="http://test"
#         ) as ac:
#             response = await ac.post("/upload", files=test_file_1)

#         # Проверка, что файл был загружен
#         assert response.status_code == 200
#         assert (
#             mock_upload_to_minio.call_count == 1
#         )  # Загрузка файла должна быть выполнена

#         # Загрузка второго файла с тем же названием
#         async with AsyncClient(
#             transport=ASGITransport(app=app), base_url="http://test"
#         ) as ac:
#             response = await ac.post("/upload", files=test_file_2)

#         # Проверка, что файл был перезаписан или добавлен с уникальным именем
#         assert (
#             response.status_code == 200
#         )  # Ожидаемый успешный статус для второй загрузки
#         assert (
#             mock_upload_to_minio.call_count == 2
#         )  # Загрузка второго файла должна быть выполнена

#         # Очистка зависимостей
#         app.dependency_overrides.clear()


# @pytest.mark.anyio
# async def test_upload_files_with_different_names_same_content():
#     """Тест для загрузки файлов с разными названиями, но одинаковым содержанием"""

#     # Мок двух файлов с разными именами, но одинаковым содержимым
#     test_file_1 = {"file": ("file1.zip", b"Fake ZIP content", "application/zip")}
#     test_file_2 = {"file": ("file2.zip", b"Fake ZIP content", "application/zip")}

#     # Мок сессии базы данных
#     mock_db_session = AsyncMock()

#     # Асинхронная заглушка для получения сессии БД
#     async def override_get_db():
#         yield mock_db_session

#     # Моки для работы с Minio
#     mock_file_exists = Mock(return_value=False)  # Файл не существует
#     mock_upload_to_minio = AsyncMock(return_value=True)
#     mock_delete_from_minio = AsyncMock()
#     mock_celery_task = AsyncMock()

#     # Патчи для замены реальных функций на моки
#     with (
#         patch("app.api.routers.file_exists_in_minio", mock_file_exists),
#         patch("app.api.routers.upload_to_minio", mock_upload_to_minio),
#         patch("app.api.routers.delete_from_minio", mock_delete_from_minio),
#         patch("app.api.routers.process_zip_task.apply_async", mock_celery_task),
#     ):
#         # Перегрузка зависимости для БД
#         app.dependency_overrides[get_db] = override_get_db

#         # Загрузка первого файла
#         async with AsyncClient(
#             transport=ASGITransport(app=app), base_url="http://test"
#         ) as ac:
#             response = await ac.post("/upload", files=test_file_1)

#         # Проверка, что первый файл был загружен
#         assert response.status_code == 200
#         assert (
#             mock_upload_to_minio.call_count == 1
#         )  # Загрузка первого файла должна быть выполнена

#         # Загрузка второго файла с таким же содержимым, но другим именем
#         async with AsyncClient(
#             transport=ASGITransport(app=app), base_url="http://test"
#         ) as ac:
#             response = await ac.post("/upload", files=test_file_2)

#         # Проверка, что второй файл был загружен как отдельный файл
#         assert (
#             response.status_code == 400
#         )  # Ожидаемый успешный статус для второй загрузки
#         assert (
#             mock_upload_to_minio.call_count == 1
#         )  # Загрузка второго файла должна быть выполнена

#         # Очистка зависимостей
#         app.dependency_overrides.clear()
