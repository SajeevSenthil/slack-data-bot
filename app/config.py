import os
from urllib.parse import urlparse
from dotenv import load_dotenv, find_dotenv


def _clean_env(name: str):
	value = os.getenv(name)
	if value is None:
		return None
	return value.strip().strip('"').strip("'")


# Ensure project .env is loaded even when uvicorn is started from a different cwd,
# and let .env override stale shell/session variables.
load_dotenv(find_dotenv(usecwd=True), override=True)

DATABASE_URL = _clean_env("DATABASE_URL")

POSTGRES_HOST = _clean_env("POSTGRES_HOST")
POSTGRES_DB = _clean_env("POSTGRES_DB")
POSTGRES_USER = _clean_env("POSTGRES_USER")
POSTGRES_PASSWORD = _clean_env("POSTGRES_PASSWORD")
POSTGRES_PORT = _clean_env("POSTGRES_PORT")

if DATABASE_URL and (not POSTGRES_HOST or not POSTGRES_DB or not POSTGRES_USER):
    parsed = urlparse(DATABASE_URL)
    POSTGRES_HOST = POSTGRES_HOST or parsed.hostname
    POSTGRES_DB = POSTGRES_DB or parsed.path.lstrip("/")
    POSTGRES_USER = POSTGRES_USER or parsed.username
    POSTGRES_PASSWORD = POSTGRES_PASSWORD or parsed.password
    POSTGRES_PORT = POSTGRES_PORT or parsed.port

GOOGLE_API_KEY = _clean_env("GOOGLE_API_KEY")
SLACK_BOT_TOKEN = _clean_env("SLACK_BOT_TOKEN")
SLACK_SIGNING_SECRET = _clean_env("SLACK_SIGNING_SECRET")
PUBLIC_BASE_URL = _clean_env("PUBLIC_BASE_URL")