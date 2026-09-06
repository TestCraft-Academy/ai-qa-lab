import json
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

load_dotenv(find_dotenv())

class TestCase(BaseModel):
    id: str = Field(description="Format TC-###")
    title: str
    expected_result: str
    automated: bool

client = genai.Client()
model_name = "gemini-3.8-flash"

response = client.models.generate_content(
    model=model_name,
    contents="Generate a test case for user login with invalid password.",
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TestCase,
    )
)

parsed = json.loads(response.text)
print("Valid JSON Output:")
print(json.dumps(parsed, indent=2))
print("\nKey Takeaway: Schema validation ensures valid types, but semantic validity requires business logic checks.")