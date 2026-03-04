import pandas as pd
import tempfile
from fastapi.responses import FileResponse
from app.state import last_query


def generate_csv():

    columns = last_query["columns"]
    rows = last_query["rows"]

    if not rows:
        return None

    df = pd.DataFrame(rows, columns=columns)

    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")

    df.to_csv(temp.name, index=False)

    return temp.name