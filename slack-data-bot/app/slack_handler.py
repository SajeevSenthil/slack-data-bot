from fastapi import APIRouter, Request
from app.database import run_query
from app.llm_sql import generate_sql

router = APIRouter()

@router.post("/slack/ask-data")
async def ask_data(request: Request):
    form_data = await request.form()
    user_text = form_data.get("text")

    try:
        # Generate SQL using Gemini
        sql = generate_sql(user_text)
        print("Generated SQL:", sql)

        # Remove line breaks and extra spaces that might confuse the check
        clean_sql = sql.strip().replace('\n', ' ').replace('\r', '')

        # Safety check
        if not clean_sql.upper().startswith("SELECT"):
            return {
                "response_type": "in_channel",
                "text": "Only SELECT queries are allowed."
            }

        columns, rows = run_query(sql)

        if not rows:
            return {
                "response_type": "in_channel",
                "text": "No data found."
            }

        # Format results nicely
        # Create header
        result = " | ".join(columns) + "\n"
        result += "-" * len(result) + "\n"
        
        # Add rows
        for row in rows:
            result += " | ".join(str(val) for val in row) + "\n"

        return {
            "response_type": "in_channel",
            "text": f"```{result}```"
        }

    except Exception as e:
        return {
            "response_type": "in_channel",
            "text": f"Error:\n```{str(e)}```"
        }