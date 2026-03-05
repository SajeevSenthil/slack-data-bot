# Slack AI Data Bot

Slack AI Data Bot is a FastAPI-based Slack application that converts natural language business questions into SQL using LangChain + Gemini, executes queries on PostgreSQL, and returns formatted results in Slack.

The project also supports:

- CSV export from Slack message actions
- Chart generation and upload to Slack
- Scheduled report delivery via n8n
- LRU caching for repeated NL to SQL prompts

## Table of Contents

1. Project Overview
2. Features
3. Architecture
4. Project Structure
5. Prerequisites
6. Environment Variables
7. Local Setup
8. Slack App Setup
9. API Endpoints
10. n8n Scheduled Reports
11. LRU Cache Design
12. Screenshots
13. Troubleshooting

## Project Overview

The bot exposes Slack endpoints for:

- `/slack/ask-data`: generate SQL from natural language, execute query, and return preview
- `/slack/export`: export previous query results as downloadable CSV

For scheduled automation, the bot also exposes:

- `/reports/scheduled`: send daily CSV and chart report to a Slack channel (triggered by n8n)

## Features

| Feature | Description |
|---|---|
| NL to SQL | Converts user question to a single PostgreSQL `SELECT` query |
| Query execution | Executes SQL against PostgreSQL and returns tabular preview |
| CSV export | Slack button uploads a downloadable CSV file to the same channel |
| Chart upload | Generates a chart from 2-column numeric result sets and uploads it |
| LRU cache | Caches repeated prompts with capacity `200` to reduce LLM latency and cost |
| Scheduled reports | n8n workflow calls backend API to send daily report files to Slack |

## Architecture

### Architecture Diagram (work flow)

```mermaid
flowchart LR
	U[Slack User] -->|/ask-data| S[Slack Platform]
	S --> A1[FastAPI: /slack/ask-data]
	A1 -->|ACK < 3s| S
	A1 --> Q[Background Query Processor]

	Q --> C{LRU Cache\ncapacity 200}
	C -->|Hit| Q
	C -->|Miss| LLM[LangChain + Gemini]
	LLM --> Q

	Q --> DB[(PostgreSQL)]
	DB --> Q
	Q --> MSG[Result Formatter]
	MSG --> S

	S -->|Export CSV click| A2[FastAPI: /slack/export]
	A2 -->|ACK < 3s| S
	A2 --> E[Background Export Processor]
	E --> CSV[CSV Bytes]
	E --> CH[Chart Bytes]
	CSV --> SLK[Slack File Upload API]
	CH --> SLK
	SLK --> S

	N8N[n8n Scheduler] -->|POST /reports/scheduled| A3[FastAPI: /reports/scheduled]
	A3 --> DB
	DB --> A3
	A3 --> SLK
```

### Architecture Diagram (Detailed Business logic)

```mermaid
flowchart TD
	U[Slack User]
	S[Slack Platform]
	N8N[n8n Scheduler]

	subgraph API[FastAPI Backend]
		A1[POST /slack/ask-data]
		A2[POST /slack/export]
		A3[POST /reports/scheduled]
	end

	subgraph CORE[Core Logic]
		P1[process_query background task]
		P2[process_export background task]
		R1[scheduled report logic]
		FMT[Result formatter and Slack blocks]
		CSV[CSV generator in-memory]
		CH[Chart generator in-memory PNG]
		STORE[In-memory result store]
		AUTH[Internal token validator]
	end

	subgraph LLM[NL to SQL Layer]
		C1[LRU Cache DLL + HashMap capacity 200]
		L1[LangChain Prompt]
		L2[Gemini 2.5 Flash]
	end

	DB[(PostgreSQL)]
	SU1[Slack files.getUploadURLExternal]
	SU2[Upload bytes to pre-signed URL]
	SU3[Slack files.completeUploadExternal]

	U -->|/ask-data question| S
	S --> A1
	A1 -->|Immediate ACK < 3s| S
	A1 --> P1

	P1 --> C1
	C1 -->|Cache hit| P1
	C1 -->|Cache miss| L1
	L1 --> L2
	L2 -->|SQL| P1
	P1 -->|SELECT query| DB
	DB -->|columns and rows| P1

	P1 --> STORE
	P1 --> FMT
	FMT -->|SQL preview + result preview + export button| S

	P1 --> CH
	CH -->|chart bytes| SU1
	SU1 --> SU2 --> SU3
	SU3 -->|chart.png posted| S

	U -->|Click Export CSV| S
	S --> A2
	A2 -->|Immediate ACK < 3s| S
	A2 --> P2
	P2 --> STORE
	STORE -->|lookup by query_id| P2
	P2 --> CSV
	CSV -->|csv bytes| SU1
	SU3 -->|report.csv posted| S

	N8N -->|POST /reports/scheduled + X-Internal-Token| A3
	A3 --> AUTH
	AUTH -->|valid| R1
	AUTH -->|invalid 401| N8N
	R1 --> DB
	DB --> R1
	R1 --> CSV
	R1 --> CH
	CSV --> SU1
	CH --> SU1
	SU3 -->|daily_report.csv + daily_report_chart.png| S
```

## Project Structure

```text
slack-data-bot/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── db/
│   │   └── postgres.py
│   ├── llm/
│   │   ├── lru_cache.py
│   │   └── sql_generator.py
│   ├── slack/
│   │   └── handler.py
│   └── reports/
│       └── scheduler.py
├── assets/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Prerequisites

| Tool | Version (Recommended) |
|---|---|
| Python | 3.11+ |
| Docker Desktop | Latest |
| Git | Latest |
| Slack Workspace Admin Access | Required for app setup |
| n8n | Docker-based local instance |

## Environment Variables

Create `.env` in repository root.

| Variable | Required | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | Yes | Slack bot OAuth token (`xoxb-...`) |
| `SLACK_SIGNING_SECRET` | Yes | Slack request verification secret |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `GOOGLE_API_KEY` | Yes | Gemini API key used by LangChain |
| `PUBLIC_BASE_URL` | Optional | Public base URL for external references |
| `INTERNAL_REPORT_TOKEN` | Yes (for n8n) | Shared secret for `/reports/scheduled` |

Example:

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/salesdb
GOOGLE_API_KEY=...
PUBLIC_BASE_URL=https://your-ngrok-domain.ngrok-free.dev
INTERNAL_REPORT_TOKEN=replace_with_strong_random_value
```

## Local Setup

1. Clone and enter repository.

```bash
git clone https://github.com/SajeevSenthil/slack-data-bot.git
cd slack-data-bot
```

2. Create and activate virtual environment.

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies.

```bash
pip install -r requirements.txt
```

4. Start PostgreSQL (Docker).

```bash
docker-compose up -d
```

5. Start FastAPI server.

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

6. Expose local server to Slack (if needed).

```bash
ngrok http 8000
```

## Slack App Setup

Use `https://api.slack.com/apps`.

| Section | Setting |
|---|---|
| Slash Commands | `/ask-data` -> `https://<ngrok>/slack/ask-data` |
| Interactivity & Shortcuts | Enabled -> `https://<ngrok>/slack/export` |
| OAuth Bot Scopes | `commands`, `chat:write`, `files:write` |
| Install App | Install or Reinstall to Workspace |

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/slack/ask-data` | Handle slash command, run NL->SQL flow |
| `POST` | `/slack/export` | Handle export button click and upload CSV |
| `POST` | `/reports/scheduled` | Send scheduled daily report (n8n trigger) |

### Scheduled Endpoint Contract

| Item | Value |
|---|---|
| Query param | `channel_id=<SLACK_CHANNEL_ID>` |
| Header | `X-Internal-Token: <INTERNAL_REPORT_TOKEN>` |

Example manual test:

```bash
curl -X POST "http://127.0.0.1:8000/reports/scheduled?channel_id=C0AJHET28BU" \
	-H "X-Internal-Token: <YOUR_INTERNAL_REPORT_TOKEN>"
```

## n8n Scheduled Reports

1. Start n8n in Docker:

```bash
docker volume create n8n_data
docker run -d --name n8n-local -p 5678:5678 -v n8n_data:/home/node/.n8n n8nio/n8n
```

2. Open `http://localhost:5678` and create owner account.
3. Create workflow:

| Node | Configuration |
|---|---|
| Schedule Trigger | Daily or weekday schedule, timezone `Asia/Kolkata` |
| HTTP Request | `POST http://host.docker.internal:8000/reports/scheduled` |
| HTTP Query Param | `channel_id=<target_channel_id>` |
| HTTP Header | `X-Internal-Token=<INTERNAL_REPORT_TOKEN>` |

4. Execute once to validate.
5. Activate workflow.

## LRU Cache Design

The NL->SQL module includes a custom LRU cache (`capacity=200`) implemented using a doubly linked list and hashmap.

| Component | Purpose |
|---|---|
| HashMap (`key -> node`) | O(1) lookup |
| Doubly Linked List | O(1) recency updates and eviction |
| Lock | Thread-safe operations in concurrent request handling |

Cache key format:

```text
<prompt_version>::<normalized_question>
```

Example verification command:

```bash
python - <<'PY'
import time
from app.llm.sql_generator import generate_sql

q = "show revenue by region"
t1 = time.perf_counter(); generate_sql(q); d1 = time.perf_counter() - t1
t2 = time.perf_counter(); generate_sql(q); d2 = time.perf_counter() - t2

print(f"First call:  {d1:.4f}s")
print(f"Second call: {d2:.4f}s")
print(f"Speedup:     {d1 / max(d2, 1e-9):.2f}x")
PY
```

## Screenshots

| Scenario | Preview |
|---|---|
| Slash command result with export button | ![Slack query result](assets/example1%20(1).png) |
| CSV and chart delivered in Slack | ![CSV and chart output](assets/example1%20(2).png) |
| n8n workflow (schedule + HTTP trigger) | ![n8n workflow](assets/n8n%20workflow.png) |
| Daily report output | ![Daily report](assets/daily_report.png) |
| LRU cache timing validation | ![LRU validation](assets/lru_eval.png) |

## Troubleshooting

| Issue | Likely Cause | Fix |
|---|---|---|
| `Unauthorized` on `/reports/scheduled` | Token mismatch | Verify `INTERNAL_REPORT_TOKEN` and header `X-Internal-Token` |
| Slack export shows timeout warning | Endpoint response exceeded 3s | Keep immediate acknowledgment and move upload to background task |
| `method_deprecated` while uploading files | Deprecated Slack upload API | Use external upload flow (`files.getUploadURLExternal` + `files.completeUploadExternal`) |
| `API_KEY_INVALID` from Gemini | Wrong key or stale env values | Check `GOOGLE_API_KEY`, restart server, verify `.env` loading |
| No scheduled rows found | Report date filter has no data | Insert test rows for yesterday or adjust report query |

## License

This project is licensed under the terms in `LICENSE`.
