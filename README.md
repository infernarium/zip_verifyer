# Оглавление

- [Оглавление](#оглавление)
- [Общее описание](#общее-описание)
- [ВАЖНО](#важно)
- [Структура проектаzip_verifier](#структура-проектаzip_verifier)
- [API](#api)
- [База данных](#база-данных)
  - [Таблицы](#таблицы)
    - [Таблица `task_results`](#таблица-task_results)
      - [Возможные значения `status`:](#возможные-значения-status)
  - [Схемы](#схемы)
    - [`UploadResponse`](#uploadresponse)
    - [`TestResults`](#testresults)
    - [`ResultsResponse`](#resultsresponse)
  - [Миграции (alembic)](#миграции-alembic)
    - [Подготовка](#подготовка)
    - [Описание процесса миграций](#описание-процесса-миграций)
- [Развёртывание](#развёртывание)
  - [Запуск проекта](#запуск-проекта)
- [Тестирование](#тестирование)
- [Общие результаты](#общие-результаты)
  - [Получилось](#получилось)
  - [Не получилось](#не-получилось)

# Общее описание

Этот сервис выполняет верификацию ZIP-архивов, проверяет их содержимое, взаимодействует с MinIO для хранения файлов и использует Celery для асинхронной обработки с запросами к внешним API. В качестве кэша и брокера для Celery используется Redis.

Функционал:

- Загрузка ZIP-архива (POST /upload) с проверкой хэш-суммы
- Асинхронная обработка архива с эмуляцией запросов к внешним API
- Получение результата анализа (GET /results/{task_id})
- Использование PostgreSQL для хранения информации о задачах
- Хранение ZIP-архивов в MinIO
- Синхронная очередь задач Celery + Redis
- Кэширование результатов в Redis

# ВАЖНО

При загрузке архивов может происходить ошибка. Она не связана ни с чем и генерируется случайным образом в `external_apis.py`, для проверки статуса соответствующей задачи в бд. Поскольку Celery настроен на повторение задачи в случае её не выполнения - через 180 секунд будет происходить повторная попытка обработка архива во внешних api.

# Структура проектаzip_verifier

```text
├ 📂 app - исходный код приложения
│ ├ 📂 api - обработчики FastAPI
│ │ ├ routers.py - набор эндпоинтов
│ │ └ schemas.py - схемы ответов
│ │
│ ├ 📂 db - модули для работы с базой данных
│ │ ├ base.py - базовый класс для моделей
│ │ └ session.py - создание соединений с базой данных
│ │
│ ├ 📂 models - описание моделей SQLAlchemy
│ │ └ task_result.py - модель задачи обработки архива
│ │
│ ├ 📂 services - бизнес-логика (Celery, MinIO, внешние api)
│ │ ├ celery.py - создание клиента м задач celery
│ │ └ minio_client.py - работа с minio клиентом
│ │
│ ├ main.py - точка входа FastAPI
│ ├ config.py - файл настроек
│ └ check_hash.py - функция для хэширования архивов
│
├ 📂 external_api - mock сервисы, эмулирующие получение характеристик архива
│ ├ coverage.py - получение покрытия и багов
│ ├ smells.py - получение запахов кода
│ └ vulnerabilities.py - получение уязвимостей
│
├ 📂 migrations - миграции Alembic
│ ├ 📂 versions/ - файлы с версиями миграций
│ ├ script.py.mako - шаблон для новых миграций
│ └ env.py - основной файл Alembic
│
├ 📂 tests - тесты приложения
│
├ .env - переменные окружения
├ .gitignore - список файлов и папок, игнорируемых Git
├ alembic.ini - конфигурационный файл Alembic для управления миграциями
├ docker-compose.yml - файл для оркестрации контейнеров Docker
├ Dockerfile - инструкция для сборки образа FastAPI-приложения
├ poetry.lock - зафиксированные версии зависимостей Poetry
├ pyproject.toml - конфигурация Poetry
└ README.md - документация проекта
```

# API

# База данных

В соответствии с т.з. используется PostgreSQL.

## Таблицы

### Таблица `task_results`

Хранит информацию о задачах проверки загруженных ZIP-архивов.

| Поле    | Тип                                            | Описание                         |
| ------- | ---------------------------------------------- | -------------------------------- |
| task_id | `STRING (PRIMARY KEY)`                         | Уникальный идентификатор задачи. |
| status  | `ENUM (PENDING, IN_PROGRESS, SUCCESS, FAILED)` | Текущий статус задачи.           |
| results | `JSONB (nullable)`                             | Результаты проверки (метрики).   |

#### Возможные значения `status`:

- **PENDING** – задача создана, но еще не запущена.
- **IN_PROGRESS** – задача выполняется.
- **SUCCESS** – задача успешно завершена.
- **FAILED** – произошла ошибка во время выполнения.

Данные из этой таблицы используются для отслеживания состояния проверки загруженных ZIP-архивов и получения аналитической информации. В коде `task_id` генерируется как hash от загруженного архива.

## Схемы

### `UploadResponse`

Ответ при загрузке ZIP-архива.

| Поле    | Тип   | Описание                         |
| ------- | ----- | -------------------------------- |
| task_id | `str` | Уникальный идентификатор задачи. |

---

### `TestResults`

Результаты анализа кода внутри ZIP-архива.

| Поле             | Тип              | Описание                                |
| ---------------- | ---------------- | --------------------------------------- |
| overall_coverage | `float`          | Общий процент покрытия кода тестами.    |
| bugs             | `Dict[str, int]` | Количество ошибок по категориям.        |
| code_smells      | `Dict[str, int]` | Количество "Code Smells" по категориям. |
| vulnerabilities  | `Dict[str, int]` | Количество уязвимостей по категориям.   |

---

### `ResultsResponse`

Ответ API с результатами проверки.

| Поле    | Тип                     | Описание                                          |
| ------- | ----------------------- | ------------------------------------------------- |
| status  | `TaskStatusEnum`        | Текущий статус задачи (PENDING, SUCCESS и т. д.). |
| results | `Optional[TestResults]` | Итоговые результаты анализа (если есть).          |

- Если `status` = `PENDING` или `IN_PROGRESS`, поле `results` будет `null`.
- Если `status` = `SUCCESS`, поле `results` будет содержать метрики анализа.
- Если `status` = `FAILED`, `results` будет `null`.

## Миграции (alembic)

Alembic используется для управления схемой базы данных, отслеживания изменений и применения их в виде версий миграций.

### Подготовка

В файле .env необходимо указывать адрес базы данных, к которой будут применяться миграции, в меременной DATABASE_URL.
**Пример для запуска в docker-compose**

```ini
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@zip-veryfier-postgres:5432/${POSTGRES_DB}
```

**Пример для запуска в среде программирования**

```ini
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}
```

В случа замены переменных среды для базы данных, переменную DATABASE_URL нужно менять в соответствии.

### Описание процесса миграций

1. **Создание новой миграции**
   ```bash
   poetry run alembic revision --autogenerate -m "Описание изменений"
   ```
2. **Применение миграция**
   ```bash
   poetry run alembic upgrade head
   ```
3. **Откат последней миграции**
   ```bash
   poetry run alembic downgrade -1
   ```

# Развёртывание

Для развёртывания одной командой необходимо удостовериться, что в файлах `.env` и `docker-compose.yml` заданы корректные настройки подключения к базе данных, хранилищу MinIO и другим сервисам.

Перед запуском контейнеров проверьте, что:

- В `.env` заданы корректные переменные окружения, включая доступ к базе данных (`DATABASE_URL`), MinIO (`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`).
- В `docker-compose.yml` сервисы используют корректные переменные и имена контейнеров.

Пример файла `.env` для запуска docker-compose

```bash
# PostgreSQL
POSTGRES_DB=zip_verifier
POSTGRES_USER=zip_admin
POSTGRES_PASSWORD=supersecurepassword

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadminpassword
MINIO_BUCKET_NAME=zip-archives

# Keycloak
KC_ADMIN=admin
KC_ADMIN_PASSWORD=adminpassword

# FastAPI
MINIO_ENDPOINT=minio:9000
DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@zip_verifier_postgres:5432/${POSTGRES_DB}

# Celery
CELERY_BROKER_URL=redis://zip_verifier_redis:6379/0
```

Пример docker-compose:

```yaml
networks:
  zip_verifier_network:
    driver: bridge

services:
  postgres:
    image: postgres:16
    container_name: zip_verifier_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - zip_verifier_network

  minio:
    image: minio/minio:latest
    container_name: zip_verifier_minio
    restart: unless-stopped
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports:
      - "9000:9000"
      - "9001:9001"
    command: server --address 0.0.0.0:9000 --console-address 0.0.0.0:9001 /data
    volumes:
      - minio_data:/data
    networks:
      - zip_verifier_network

  redis:
    image: redis:7
    container_name: zip_verifier_redis
    restart: unless-stopped
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - zip_verifier_network

  alembic:
    build: .
    container_name: zip_verifier_alembic
    restart: on-failure:5
    env_file: .env
    depends_on:
      - postgres
    command: >
      poetry run alembic upgrade head
    networks:
      - zip_verifier_network

  fastapi:
    build: .
    container_name: zip_verifier_fastapi
    restart: unless-stopped
    env_file: .env
    depends_on:
      alembic:
        condition: service_completed_successfully
      redis:
        condition: service_started
      minio:
        condition: service_started
    ports:
      - "8000:8000"
    command: >
      poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    networks:
      - zip_verifier_network

  celery:
    build: .
    container_name: zip_verifier_celery
    restart: unless-stopped
    env_file: .env
    depends_on:
      fastapi:
        condition: service_started
      redis:
        condition: service_started
    command: >
      poetry run celery -A app.services.celery worker -l info -P eventlet
    networks:
      - zip_verifier_network

volumes:
  postgres_data:
  minio_data:
  redis_data:
```

## Запуск проекта

После проверки конфигурации выполните:

```bash
docker-compose -p zip_tester up --build -d
```

Для очистки всех контейнеров и их выключения использовать команду

```bash
docker-compose --project_name zip_tester down -v
```

После запуска проекта доступ к эндпоинтам fastapi осущствляется по адресу `http://localhost:8000/docs`.

# Тестирование

Запуске тестов осузествляется следующей командой

```
poetry pytest tests
```

# Общие результаты

## Получилось

- сделать необходимые эндпоинты
- добавить асинхронность
- сделать фоновую обработку задач
- сделать развёртывание через docker-compose
- добавить кэширование результатов
- написать тесты
- сделать валидацию данных
- сделать обработку ошибок

## Не получилось

- использовать одну сессию вместо заведение 2-х штук для синхронного и асинхронного выполнения (при синхронном выполнении ломается асинхронность fastapi, а при асинхронном ломается celery)
- сделать аутентификацию через keycloak (в докере всё запускается, keycloak создаёт свои таблички в postgres-е, я ручками создаю realm и user, но оно всё равно не работает - нельзя подключится по этому адресу. Пытался сделать через другую библиотеку, но там в документации пример с keycloak 16 версии, который докер отказывается скачивать)
- сделать структуру проекта в соответствии с api - service - repository (сначала сделал тесты, а потом увидел как правильно организовывать структуру, если её поменять - упадут все тесты)
- сделать обработку фоновых задач через fastapi Backgroundtasks (основной проблемой оказалась передача сессии базы данных в task. Если делать это в маршруте через аргументы, то запрос к upload висит до момента выполнения задачи. Если заводить новую сессию и передавать её - зависает следующий запрос. Возможно, асинхронные запросы всё-так являются синхронными, но скорее всего просто не правильно передавал сессию)
