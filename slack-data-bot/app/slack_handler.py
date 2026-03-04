from fastapi import APIRouter, Request, BackgroundTasks
from fastapi.responses import FileResponse
import json

from app.database import run_query
from app.llm_sql import generate_sql
from app.utils import send_slack_response
from app.state import last_query
from app.report import upload_csv_to_slack


router = APIRouter()


# Background query processor

def process_query(user_text, response_url):

    try:

        # Generate SQL using LLM
        sql = generate_sql(user_text)

        print("Generated SQL:", sql)

        clean_sql = sql.strip().replace("\n", " ").replace("\r", "")

        if not clean_sql.upper().startswith("SELECT"):
            send_slack_response(response_url, "Only SELECT queries allowed.")
            return

        columns, rows = run_query(sql)

        if not rows:
            send_slack_response(response_url, "No data found.")
            return

        # Store last query for report export
        last_query["columns"] = columns
        last_query["rows"] = rows

        # Format result nicely
        result = " | ".join(columns) + "\n"
        result += "-" * 50 + "\n"

        for row in rows:
            result += " | ".join(str(val) for val in row) + "\n"

        # Send Slack message with export button
        send_slack_response(
            response_url,
            f"```{result}```",
            with_button=True
        )

    except Exception as e:

        send_slack_response(
            response_url,
            f"Error:\n```{str(e)}```"
        )


# Slash command handler

@router.post("/slack/ask-data")
async def ask_data(request: Request, background_tasks: BackgroundTasks):

    form_data = await request.form()

    user_text = form_data.get("text")
    response_url = form_data.get("response_url")

    # Run query processing in background
    background_tasks.add_task(process_query, user_text, response_url)

    # Immediate response (Slack requires <3s)
    return {
        "response_type": "ephemeral",
        "text": "Processing your query..."
    }



# CSV export handler

@router.post("/slack/export")
async def export_csv(request: Request, background_tasks: BackgroundTasks):

    form_data = await request.form()
    payload = json.loads(form_data["payload"])

    channel_id = payload["channel"]["id"]

    # Run export in background
    background_tasks.add_task(upload_csv_to_slack, channel_id)

    # Immediate response to Slack (within 3 seconds)
    return {
        "response_type": "ephemeral",
        "text": "Generating CSV report..."
    }