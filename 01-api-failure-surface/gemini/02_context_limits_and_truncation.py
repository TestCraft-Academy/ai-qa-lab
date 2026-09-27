"""
02_context_limits_and_truncation.py
Demonstrates silent truncation defects when output token limits are reached,
how reasoning/thinking tokens consume output budgets, and downstream parser crashes.
"""

import json
from dotenv import load_dotenv, find_dotenv
from google import genai
from google.genai import types

load_dotenv(find_dotenv())

client = genai.Client()
model_name = "gemini-3.8-flash"

def print_section(title: str):
    print(f"\n{'='*75}\n[TEST SCENARIO] {title}\n{'='*75}")

# ==============================================================================
# SCENARIO 1: Silent Truncation via FinishReason.MAX_TOKENS
# ==============================================================================
print_section("1. Silent Truncation via FinishReason.MAX_TOKENS")
print("Goal: Demonstrate that generation can abruptly terminate mid-sentence without throwing an exception.\n")

prompt = "Write a comprehensive 500-word analysis of why automated UI tests become flaky over time."

# Artificially constrain output tokens to force truncation (disable thinking budget to demonstrate mid-sentence cut)
response = client.models.generate_content(
    model=model_name,
    contents=prompt,
    config=types.GenerateContentConfig(
        max_output_tokens=35,
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )
)

candidate = response.candidates[0]
finish_reason = candidate.finish_reason

print(f"Generated text snippet:\n\"{response.text}\"\n")
print(f"HTTP/SDK Status       : SUCCESS (HTTP 200, no exception raised)")
print(f"Candidate FinishReason: {finish_reason}")

print("\n[QA DEFECT AUDIT]:")
if finish_reason == types.FinishReason.MAX_TOKENS:
    print("  >>> DEFECT CONFIRMED: Response was abruptly cut off mid-sentence!")
    print("      Client application received HTTP 200, but the user received an incomplete answer.")
else:
    print(f"  Finish reason: {finish_reason}")

# ==============================================================================
# SCENARIO 2: Thinking/Reasoning Tokens Starving Output Content
# ==============================================================================
print_section("2. Thinking Tokens Exhausting Output Quota (Zero-Text Defect)")
print("Goal: Observe what happens when reasoning models consume the entire token budget during thinking.\n")

# With thinking enabled by default, 30 tokens get completely consumed by internal thoughts
thinking_response = client.models.generate_content(
    model=model_name,
    contents="Explain why distributed transactions fail in microservices.",
    config=types.GenerateContentConfig(
        max_output_tokens=30
    )
)

cand = thinking_response.candidates[0]
print(f"Finish Reason: {cand.finish_reason}")
print(f"Output Text  : {thinking_response.text}")
if thinking_response.text is None and cand.finish_reason == types.FinishReason.MAX_TOKENS:
    print("\n[QA DEFECT AUDIT]: ZERO USER-FACING TOKENS RETURNED!")
    print("  Root Cause: In reasoning models (Gemini 2.5/3.x), thinking tokens count against max_output_tokens.")
    print("  If max_output_tokens is too low, the model runs out of budget before producing any text!")

# ==============================================================================
# SCENARIO 3: Downstream Data Corruption (Truncated JSON)
# ==============================================================================
print_section("3. Downstream Data Corruption (Truncated JSON)")
print("Goal: Show how silent truncation causes unhandled crashes in downstream services.\n")

json_prompt = (
    "Generate a JSON list of 10 common UI automated test failure categories with "
    "fields: id, category, root_cause, mitigation."
)

# Output token cap is too small for 10 records
truncated_json_response = client.models.generate_content(
    model=model_name,
    contents=json_prompt,
    config=types.GenerateContentConfig(
        max_output_tokens=70,
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(thinking_budget=0)
    )
)

raw_output = truncated_json_response.text
print(f"Raw Output Received:\n{raw_output}\n")

try:
    data = json.loads(raw_output)
    print("JSON parsed successfully.")
except json.JSONDecodeError as e:
    print(f"[QA DEFECT AUDIT] Downstream Pipeline Crash: {type(e).__name__}: {e}")
    print("  Root Cause: Closing brackets and trailing fields were never emitted due to token starvation.")

print("\n[SDET Takeaways]:")
print("  1. In automated tests, NEVER assert solely on HTTP 200 or non-empty response text.")
print("  2. Always explicitly assert: `assert candidate.finish_reason == types.FinishReason.STOP`.")
print("  3. Be mindful that reasoning/thinking tokens consume `max_output_tokens`. Always budget at least")
print("     1,000–2,000 tokens when using reasoning models.")
print("  4. Workshop Lab Reference: See Lab 01 in 'ai-qa-workshops' for writing automated finish-reason assertions.")
