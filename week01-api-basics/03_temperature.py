from google import genai
from google.genai import types

client = genai.Client()
model_name = "gemini-3.8-flash"
prompt = "Define the term 'Regression Test' in exactly one punchy sentence."

for temp in [0.0, 1.0, 2.0]:
    print(f"\n--- Testing at Temperature: {temp} ---")
    for run_idx in range(1, 4):
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(temperature=temp)
        )
        print(f"Run {run_idx}: {response.text.strip()}")