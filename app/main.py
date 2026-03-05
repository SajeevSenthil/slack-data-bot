from fastapi import FastAPI
from app.slack.handler import router as slack_router
from app.reports.scheduler import router as reports_router


app = FastAPI()

app.include_router(slack_router)
app.include_router(reports_router)


