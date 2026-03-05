from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from app.config import GOOGLE_API_KEY
from app.llm.lru_cache import LRUCache


PROMPT_VERSION = "v1"
SQL_CACHE = LRUCache(capacity=200)

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is missing. Check .env loading and key name.")

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0
)

template = """
You are a SQL generator.

Table: public.sales_daily

Columns:
date
region
category
revenue
orders
created_at

Rules:
- Return ONLY a PostgreSQL SELECT query
- No explanations
- No markdown
- Single query only

Question:
{question}
"""

prompt = PromptTemplate(
    input_variables=["question"],
    template=template
)


def _normalize_question(question):
    return " ".join(question.strip().lower().split())


def _cache_key(question):
    return f"{PROMPT_VERSION}::{_normalize_question(question)}"


def generate_sql(question):
    key = _cache_key(question)
    cached_sql = SQL_CACHE.get(key)
    if cached_sql:
        return cached_sql

    chain = prompt | llm
    response = chain.invoke({"question": question})
    sql = response.content.strip()
    SQL_CACHE.put(key, sql)
    return sql