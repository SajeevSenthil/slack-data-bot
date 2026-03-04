import pandas as pd
import tempfile
from slack_sdk import WebClient
import os
from app.state import last_query


def upload_csv_to_slack(channel):

    columns = last_query["columns"]
    rows = last_query["rows"]

    if not rows:
        return "No query results available."

    df = pd.DataFrame(rows, columns=columns)

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")

    df.to_csv(temp.name, index=False)

    client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

    client.files_upload_v2(
        channel=channel,
        file=temp.name,
        title="Query Report",
        filename="report.csv"
    )

    return "Report uploaded."