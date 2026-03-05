from fastapi import APIRouter, Request, BackgroundTasks
from app.llm.sql_generator import generate_sql
from app.db.postgres import run_query
from app.config import SLACK_BOT_TOKEN
import requests
import uuid
import csv
import json
from io import StringIO, BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

router = APIRouter(prefix="/slack")

# Store recent query results for Slack interactive CSV export.
LAST_QUERY_BY_ID = {}


def format_rows(columns, rows, max_rows=10):

    if not rows:
        return "No results."

    preview_rows = rows[:max_rows]
    formatted = ""

    if columns:
        formatted += " | ".join(columns) + "\n"
        formatted += "-" * 50 + "\n"

    for row in preview_rows:
        line = []
        for value in row:
            try:
                value = float(value)
                line.append(f"{value:,.2f}")
            except:
                line.append(str(value))

        formatted += " | ".join(line) + "\n"

    if len(rows) > max_rows:
        formatted += f"\n... showing {max_rows} of {len(rows)} rows"

    return formatted


def generate_csv(query_id, columns, rows):
    buffer = StringIO()
    writer = csv.writer(buffer)
    if columns:
        writer.writerow(columns)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def upload_file_to_slack(channel_id, file_bytes, title, filename):

    if not SLACK_BOT_TOKEN:
        return "Slack bot token is missing.", False, None

    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}

    try:
        # Step 1: Ask Slack for a temporary upload URL.
        step1 = requests.post(
            "https://slack.com/api/files.getUploadURLExternal",
            headers=headers,
            data={
                "filename": filename,
                "length": len(file_bytes),
            },
            timeout=30,
        )
        step1_data = step1.json()
        if not step1_data.get("ok"):
            return f"Upload failed: {step1_data.get('error', 'unknown_error')}", False, step1_data

        upload_url = step1_data.get("upload_url")
        file_id = step1_data.get("file_id")
        if not upload_url or not file_id:
            return "Upload failed: missing upload URL or file ID.", False, step1_data

        # Step 2: Upload raw bytes to the temporary URL.
        step2 = requests.post(
            upload_url,
            data=file_bytes,
            headers={"Content-Type": "application/octet-stream"},
            timeout=60,
        )
        if step2.status_code >= 400:
            return f"Upload failed: byte upload returned HTTP {step2.status_code}.", False, None

        # Step 3: Complete the upload and share into the channel.
        step3 = requests.post(
            "https://slack.com/api/files.completeUploadExternal",
            headers=headers,
            data={
                "files": json.dumps([
                    {
                        "id": file_id,
                        "title": title,
                    }
                ]),
                "channel_id": channel_id,
            },
            timeout=30,
        )
        step3_data = step3.json()
        if not step3_data.get("ok"):
            return f"Upload failed: {step3_data.get('error', 'unknown_error')}", False, step3_data

        return "Upload successful.", True, step3_data

    except Exception as exc:
        return f"Upload failed: {str(exc)}", False, None


def upload_csv_to_slack(channel_id, csv_bytes):
    message, ok, _ = upload_file_to_slack(
        channel_id,
        csv_bytes,
        title="Query Report",
        filename="report.csv"
    )
    if ok:
        return "Report uploaded."
    return message


def generate_chart(rows):

    try:

        if len(rows[0]) != 2:
            return None

        labels = [str(r[0]) for r in rows]
        values = [float(r[1]) for r in rows]

        plt.figure(figsize=(6,4))
        plt.bar(labels, values)

        chart_buffer = BytesIO()
        plt.savefig(chart_buffer, format="png")
        plt.close()
        chart_buffer.seek(0)
        return chart_buffer.getvalue()

    except:
        return None


def process_query(question, response_url, channel_id):

    try:

        sql = generate_sql(question)

        if not sql.lower().startswith("select"):
            requests.post(response_url, json={
                "response_type": "ephemeral",
                "text": "Only SELECT queries allowed."
            })
            return

        columns, rows = run_query(sql)

        formatted = format_rows(columns, rows)

        query_id = uuid.uuid4().hex
        LAST_QUERY_BY_ID[query_id] = {
            "columns": columns,
            "rows": rows,
        }

        chart_bytes = generate_chart(rows)

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*SQL*\n```{sql}```"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Result*\n```{formatted}```"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Export CSV"
                        },
                        "action_id": "export_csv",
                        "value": query_id
                    }
                ]
            }
        ]

        requests.post(response_url, json={
            "response_type": "in_channel",
            "blocks": blocks
        })

        if chart_bytes and channel_id:
            chart_message, chart_ok, _ = upload_file_to_slack(
                channel_id,
                chart_bytes,
                title="Query Chart",
                filename="chart.png"
            )
            if not chart_ok:
                requests.post(response_url, json={
                    "response_type": "ephemeral",
                    "text": f"Chart upload skipped. {chart_message}"
                })

    except Exception as e:

        requests.post(response_url, json={
            "response_type": "ephemeral",
            "text": f"Error:\n```{str(e)}```"
        })


def process_export(query_id, channel_id, response_url):
    try:
        if not query_id or query_id not in LAST_QUERY_BY_ID:
            if response_url:
                requests.post(response_url, json={
                    "response_type": "ephemeral",
                    "text": "No stored query results found. Run /ask-data again."
                })
            return

        if not channel_id:
            if response_url:
                requests.post(response_url, json={
                    "response_type": "ephemeral",
                    "text": "Could not determine channel for export."
                })
            return

        stored = LAST_QUERY_BY_ID[query_id]
        csv_bytes = generate_csv(query_id, stored["columns"], stored["rows"])
        status = upload_csv_to_slack(channel_id, csv_bytes)

        if response_url:
            requests.post(response_url, json={
                "response_type": "ephemeral",
                "text": status
            })
    except Exception as exc:
        if response_url:
            requests.post(response_url, json={
                "response_type": "ephemeral",
                "text": f"Export failed.\n```{str(exc)}```"
            })


@router.post("/ask-data")
async def ask_data(request: Request, background_tasks: BackgroundTasks):

    form = await request.form()

    question = form.get("text")
    response_url = form.get("response_url")
    channel_id = form.get("channel_id")

    background_tasks.add_task(process_query, question, response_url, channel_id)

    return {
        "response_type": "ephemeral",
        "text": "Running query..."
    }


@router.post("/export")
async def export_csv(request: Request, background_tasks: BackgroundTasks):

    form = await request.form()
    payload = json.loads(form.get("payload", "{}"))
    response_url = payload.get("response_url")

    actions = payload.get("actions", [])
    if not actions:
        return {
            "response_type": "ephemeral",
            "text": "No export action found."
        }

    query_id = actions[0].get("value")
    channel_id = payload.get("channel", {}).get("id")

    if response_url:
        background_tasks.add_task(process_export, query_id, channel_id, response_url)
    else:
        background_tasks.add_task(process_export, query_id, channel_id, "")

    return {
        "response_type": "ephemeral",
        "text": "Generating CSV report..."
    }