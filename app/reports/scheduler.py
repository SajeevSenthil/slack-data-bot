from fastapi import APIRouter, Header, HTTPException
from app.config import INTERNAL_REPORT_TOKEN
from app.db.postgres import run_query
from app.slack.handler import generate_csv, generate_chart, upload_file_to_slack

router = APIRouter(prefix="/reports")


@router.post("/scheduled")
async def run_scheduled_report(
    channel_id: str,
    x_internal_token: str = Header(default="")
):
    if not INTERNAL_REPORT_TOKEN or x_internal_token != INTERNAL_REPORT_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    sql = """
    SELECT
      date,
      region,
      SUM(revenue) AS total_revenue,
      SUM(orders) AS total_orders
    FROM public.sales_daily
    WHERE date = CURRENT_DATE - INTERVAL '1 day'
    GROUP BY date, region
    ORDER BY total_revenue DESC;
    """

    columns, rows = run_query(sql)
    if not rows:
        return {"ok": True, "message": "No rows for yesterday"}

    csv_bytes = generate_csv("daily_report", columns, rows)
    csv_msg, csv_ok, _ = upload_file_to_slack(
        channel_id,
        csv_bytes,
        title="Daily Revenue Report",
        filename="daily_report.csv"
    )

    chart_rows = [(r[1], float(r[2])) for r in rows]  # region, total_revenue
    chart_bytes = generate_chart(chart_rows)
    chart_ok = False
    chart_msg = "Chart skipped"
    if chart_bytes:
        chart_msg, chart_ok, _ = upload_file_to_slack(
            channel_id,
            chart_bytes,
            title="Daily Revenue Chart",
            filename="daily_report_chart.png"
        )

    return {
        "ok": True,
        "csv_uploaded": csv_ok,
        "csv_message": csv_msg,
        "chart_uploaded": chart_ok,
        "chart_message": chart_msg,
        "row_count": len(rows),
    }