"""
02_context_limits_and_truncation.py
Demonstrates silent truncation defects when output token limits are reached,
how reasoning tokens consume output budgets, and downstream parser crashes.
Adapted for OpenAI.
"""

import json
import openai
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

client = openai.OpenAI()
model_name = "gpt-4o"

def print_section(title: str):
    print(f"\n{'='*75}\n[TEST SCENARIO] {title}\n{'='*75}")

# ==============================================================================
# SCENARIO 1: Silent Truncation via finish_reason == 'length'
# ==============================================================================
print_section("1. Silent Truncation via finish_reason == 'length'")
print("Goal: Demonstrate that generation can abruptly terminate mid-sentence without throwing an exception.\n")

prompt = "Write a comprehensive 500-word analysis of why automated UI tests become flaky over time."

# Artificially constrain output tokens to force truncation
response = client.chat.completions.create(
    model=model_name,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=35
)

choice = response.choices[0]
finish_reason = choice.finish_reason
generated_text = choice.message.content or ""

print(f"Generated text snippet:\n\"{generated_text}\"\n")
print(f"HTTP/SDK Status       : SUCCESS (HTTP 200, no exception raised)")
print(f"Choice finish_reason  : {finish_reason}")

print("\n[QA DEFECT AUDIT]:")
if finish_reason == "length":
    print("  >>> DEFECT CONFIRMED: Response was abruptly cut off mid-sentence!")
    print("      Client application received HTTP 200, but the user received an incomplete answer.")
else:
    print(f"  Finish reason: {finish_reason}")

# ==============================================================================
# SCENARIO 2: Thinking/Reasoning Tokens Starving Output Content
# ==============================================================================
print_section("2. Thinking Tokens Exhausting Output Quota (Zero-Text Defect)")
print("Goal: Observe what happens when reasoning models consume the entire token budget during thinking.\n")

reasoning_model = "o3-mini"
try:
    thinking_response = client.chat.completions.create(
        model=reasoning_model,
        messages=[{"role": "user", "content": "Explain why distributed transactions fail in microservices."}],
        max_completion_tokens=30
    )
    cand = thinking_response.choices[0]
    details = getattr(thinking_response.usage, "completion_tokens_details", None)
    reasoning_tokens = getattr(details, "reasoning_tokens", 0) if details else 0
    print(f"Model Used       : {reasoning_model}")
    print(f"Finish Reason    : {cand.finish_reason}")
    print(f"Reasoning Tokens : {reasoning_tokens}")
    print(f"Output Text      : {cand.message.content}")
    if (not cand.message.content or cand.message.content.strip() == "") and cand.finish_reason == "length":
        print("\n[QA DEFECT AUDIT]: ZERO USER-FACING TOKENS RETURNED!")
        print("  Root Cause: In reasoning models (OpenAI o1/o3-mini), internal reasoning tokens")
        print("  count against max_completion_tokens. If the budget is too low, the model runs out")
        print("  of budget before producing any visible text!")
except Exception as e:
    print(f"Reasoning model request note ({reasoning_model}): {e}")
    print("Demonstrating token starvation with standard model constrained to 10 tokens:")
    fallback = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": "Explain why distributed transactions fail in microservices."}],
        max_tokens=10
    )
    cand = fallback.choices[0]
    print(f"Finish Reason: {cand.finish_reason}")
    print(f"Output Text  : {cand.message.content}")

# ==============================================================================
# SCENARIO 3: Downstream Data Corruption (Truncated JSON)
# ==============================================================================
print_section("3. Downstream Data Corruption (Truncated JSON)")
print("Goal: Show how silent truncation causes unhandled crashes in downstream services.\n")

json_prompt = (
    "Generate a JSON object containing a 'tests' array with 10 common UI automated test failure categories. "
    "Each item must have fields: id, category, root_cause, mitigation."
)

# Output token cap is too small for 10 records
truncated_json_response = client.chat.completions.create(
    model=model_name,
    messages=[{"role": "user", "content": json_prompt}],
    max_tokens=70,
    response_format={"type": "json_object"}
)

raw_output = truncated_json_response.choices[0].message.content or ""
print(f"Raw Output Received:\n{raw_output}\n")
print(f"Finish Reason: {truncated_json_response.choices[0].finish_reason}")

try:
    data = json.loads(raw_output)
    print("JSON parsed successfully.")
except json.JSONDecodeError as e:
    print(f"[QA DEFECT AUDIT] Downstream Pipeline Crash: {type(e).__name__}: {e}")
    print("  Root Cause: Closing brackets and trailing fields were never emitted due to token starvation.")

print("\n[SDET Takeaways]:")
print("  1. In automated tests, NEVER assert solely on HTTP 200 or non-empty response text.")
print("  2. Always explicitly assert: `assert choice.finish_reason == 'stop'` (in OpenAI, 'length' means truncated).")
print("  3. Be mindful that reasoning models (o1, o3-mini) consume `max_completion_tokens`. Always budget at least")
print("     1,000–2,000 tokens when working with reasoning architectures.")
print("  4. Workshop Lab Reference: See Lab 01 in 'ai-qa-workshops' for writing automated finish-reason assertions.")
