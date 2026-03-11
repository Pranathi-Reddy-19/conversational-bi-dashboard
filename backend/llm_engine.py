import re
import json
from google import genai
import configparser

API_KEY = "AIzaSyDl6jZF2zRqJtHmxW_51hJckt8g3bsYKBE"
client = genai.Client(api_key=API_KEY)

def create_prompt(username: str, history: str, schema: str, last_sql: str | None = None) -> str:
    context_instruction = ""
    if last_sql:
        context_instruction = f"""
IMPORTANT CONTEXT - PREVIOUS QUERY:
The user just executed this exact SQL query:
```sql
{last_sql}
```
If the user's current request is a follow-up (e.g., "now filter by X", "show me top 5", "break this down by Y"), YOU MUST build upon the SQL query above. 
Do not start from scratch unless clearly requested. Modify the previous SQL by adding WHERE clauses, changing aggregations, or updating columns as needed while keeping the base logic.
"""

    return f"""You are a senior data analyst and SQLite expert.
You will be provided with the schema of a dataset, the conversation history, and potentially the exact last SQL query run.
Your task is to analyze the user's LAST message and generate the appropriate SQLite query(ies) and charting instructions.

If the user asks for an "overview", "summary", or "dashboard" question, you MUST generate EXACTLY 3 distinct, insightful queries and charts:
1. One query for overall totals / KPIs.
2. One query for trends over time/categories.
3. One query for top/bottom rankings.
For specific, single-point questions (e.g., "What is the total revenue?", "Show me sales by region"), generate a single query.

{context_instruction}

--------------------------------------------------
DATABASE

Table name: data_{username}
Use ONLY table `data_{username}`

Columns with Contextual Atomic Profiles:
{schema}

--------------------------------------------------
SQL RULES
• Use ONLY columns listed in the schema profiles
• Generate SELECT queries only
• NEVER use SELECT *
• Include only columns necessary for analysis

Use aggregation (SUM, AVG, COUNT, etc.) ONLY when the user asks for totals, averages, comparisons, or metrics per category.
Use GROUP BY when aggregating categories.
Use ORDER BY when ranking results.
Use aliases for computed values.

--------------------------------------------------
ADVANCED SQL
Use advanced SQL when needed:
• Subqueries
• HAVING clauses
• CTEs (WITH)
• Filtering or LIMIT before aggregation

Always prioritize correct SQL logic over simplified queries.

--------------------------------------------------
GROUP-BY LOGIC
Always use GROUP BY when visualizing metrics (SUM, AVG, COUNT, MAX, MIN) across categories.
If the question compares two numeric variables, DO NOT aggregate the data. Return row-level values and use chart_type = "scatter".
If the user refers to previous analysis like "now", "extend", "same", "filter this", or "till", continue the previous query logic by adapting the SQL from the CONVERSATION HISTORY.
If the user asks "highest", "most", "top", or "best", and expects a single answer, use LIMIT 1.

--------------------------------------------------
VISUALIZATION RULES
single metric → "none"  
category + metric → "bar"
stages/process + metric → "funnel"
date + metric → "line"  
two numeric metrics → "scatter"
two categories + metric → "heatmap"
share / distribution → "pie"

--------------------------------------------------
AXIS RULES
For bar, line, and funnel: x_axis is category/date, y_axis is the numerical metric.
For pie: x_axis is category, y_axis is numerical metric.
For scatter: x_axis and y_axis must both be numerical.
For heatmap: x_axis and y_axis are the two categories, and group_by is the numerical metric (value).
x_axis, y_axis, and group_by must exactly match column names returned by the SQL query.

--------------------------------------------------
OUTPUT FORMAT

If the question is about the data and requires SQL analysis, return exactly:
{{
"queries": [
    {{
    "title": "<Brief chart title>",
    "sql": "<SQL query>",
    "chart_type": "bar | line | pie | scatter | funnel | heatmap | none",
    "x_axis": "<column name or empty>",
    "y_axis": "<column name or empty>",
    "group_by": "<column name or empty>"
    }}
],
"follow_up_questions": ["<question 1>", "<question 2>", "<question 3>"]
}}

If the question is conversational, unrelated to the dataset, or you cannot answer it using data (e.g. "who is the president", "say hello"), return exactly:
{{
"conversational_reply": "<Direct answer or fallback message>",
"follow_up_questions": ["<suggestion 1>", "<suggestion 2>"]
}}

--------------------------------------------------
CONVERSATION HISTORY

{history}
"""

def generate_query(username: str, history: str, schema: str, last_sql: str | None = None):
    prompt = create_prompt(username, history, schema, last_sql)
    response = client.models.generate_content(
        model="models/gemini-2.5-flash",
        contents=prompt
    )
    text = response.text.strip()
    try:
        result = json.loads(text)
    except:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            return None
    return result

def validate_sql(query):
    q = query.strip().upper()
    if not (q.startswith("SELECT") or q.startswith("WITH")):
        return False

    forbidden = [
        r"\bDROP\b",
        r"\bDELETE\b",
        r"\bUPDATE\b",
        r"\bINSERT\b",
        r"\bALTER\b",
        r"\bTRUNCATE\b",
        r"\bCREATE\b",
        r"\bEXEC\b"
    ]
    for pattern in forbidden:
        if re.search(pattern, q):
            return False
    return True

