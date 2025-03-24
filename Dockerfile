FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir poetry && poetry install --no-root
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]