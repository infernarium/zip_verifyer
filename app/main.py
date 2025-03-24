# uvicorn app.main:app --reload
from fastapi import FastAPI
from app.api.routers import router


app = FastAPI(title="ZIP")

app.include_router(router)
