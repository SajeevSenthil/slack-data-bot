import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

template = """
Convert the question into SQL.

Table: sales_daily
Columns:
date
region
category
revenue
orders

Question: {question}

Return ONLY SQL.
"""

prompt = PromptTemplate.from_template(template)

chain = prompt | llm

def generate_sql(question: str):
    response = chain.invoke({"question": question})
    return response.content.strip()