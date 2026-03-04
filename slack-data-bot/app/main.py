from fastapi import FastAPI
from app.slack_handler import router

app = FastAPI()

app.include_router(router)