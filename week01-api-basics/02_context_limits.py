from dotenv import load_dotenv, find_dotenv
from google import genai
from google.genai import types

load_dotenv(find_dotenv())

client = genai.Client()
model_name = "gemini-3.8-flash"

prompt = "Write a comprehensive 500-word analysis of why automated UI tests become flaky over time."

# Force truncation failure
response = client.models.generate_content(
    model=model_name,
    contents=prompt,
    config=types.GenerateContentConfig(
        max_output_tokens=40
    )
)

candidate = response.candidates[0]
print(f"Finish Reason: {candidate.finish_reason}")
print(f"Generated text snippet:\n{response.text}\n")
print("Failure Impact: Response cuts off mid-sentence with no trailing syntax/period.")