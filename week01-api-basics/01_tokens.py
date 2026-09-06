import os
from google import genai

client = genai.Client()
model_name = "gemini-3.8-flash"

samples = {
    "Plain English": "Software testing is the process of evaluating and verifying that a software application does what it is supposed to do.",
    "Dense Code": "def qsort(a): return [] if not a else qsort([x for x in a[1:] if x<a[0]]) + [a[0]] + qsort([x for x in a[1:] if x>=a[0]])",
    "Nested JSON": '{"test_run": {"suite": "api_v1", "cases": [{"id": 1, "status": "PASSED"}, {"id": 2, "status": "FAILED"}]}}',
}

for name, text in samples.items():
    count = client.models.count_tokens(model=model_name, contents=text)
    print(f"{name:15} | Chars: {len(text):4} | Words: {len(text.split()):2} | Tokens: {count.total_tokens:3}")