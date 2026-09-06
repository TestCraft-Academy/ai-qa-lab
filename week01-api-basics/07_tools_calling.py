from google import genai
from google.genai import types

# 1. Define a tool
def get_database_record(table: str, record_id: int) -> str:
    """Fetches a database record by table name and ID."""
    if table != "users":
        raise ValueError(f"Table '{table}' not accessible.")
    return f'{{"id": {record_id}, "name": "Alice QA", "role": "admin"}}'

client = genai.Client()
model_name = "gemini-3.8-flash"

# 2. Call model with tool
response = client.models.generate_content(
    model=model_name,
    contents="Look up user ID 42 in the users table.",
    config=types.GenerateContentConfig(
        tools=[get_database_record],
        temperature=0.0
    )
)

# 3. Check for function calls
if response.function_calls:
    fc = response.function_calls[0]
    print(f"Model requested tool: {fc.name} with args: {fc.args}")
    
    # Execute tool safely
    try:
        result = get_database_record(**fc.args)
        print(f"Tool execution succeeded: {result}")
    except Exception as e:
        print(f"Tool execution failed: {e}")