import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0
)

template = """
You are a SQL generator.

Table:
sales_daily(date, region, category, revenue, orders)

Convert the question to SQL.

Only return SQL.

Question: {question}
"""

prompt = PromptTemplate(
    input_variables=["question"],
    template=template
)

chain = LLMChain(llm=llm, prompt=prompt)


def generate_sql(question):
    sql = chain.run(question)
    return sql.strip().replace("```sql", "").replace("```", "")