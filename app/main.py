from fastapi import FastAPI
from app.slack.handler import router as slack_router

app = FastAPI()

app.include_router(slack_router)


# the below one was done to test
# @app.get("/db-test")
# def db_test():
#     rows = test_connection()
#     return {"rows": rows}