from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from app.config import GOOGLE_API_KEY

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

def generate_sql(question):
    chain = prompt | llm
    response = chain.invoke({"question": question})
    return response.content.strip()