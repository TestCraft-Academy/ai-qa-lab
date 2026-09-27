"""
02_context_limits_and_truncation.py
Demonstrates silent truncation defects when output token limits are reached,
how reasoning/thinking tokens consume output budgets, and downstream parser crashes.
Adapted for Anthropic Claude.
"""

import os
import json
import anthropic
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

client = anthropic.Anthropic()
model_name = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

def print_section(title: str):
    print(f"\n{'='*75}\n[TEST SCENARIO] {title}\n{'='*75}")

# ==============================================================================
# SCENARIO 1: Silent Truncation via stop_reason == 'max_tokens'
# ==============================================================================
print_section("1. Silent Truncation via stop_reason == 'max_tokens'")
print("Goal: Demonstrate that generation can abruptly terminate mid-sentence without throwing an exception.\n")

prompt = "Write a comprehensive 500-word analysis of why automated UI tests become flaky over time."

# Artificially constrain output tokens to force truncation
response = client.messages.create(
    model=model_name,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=35
)

stop_reason = response.stop_reason
generated_text = "".join(block.text for block in response.content if hasattr(block, "text"))

print(f"Generated text snippet:\n\"{generated_text}\"\n")
print(f"HTTP/SDK Status     : SUCCESS (HTTP 200, no exception raised)")
print(f"Message stop_reason : {stop_reason}")

print("\n[QA DEFECT AUDIT]:")
if stop_reason == "max_tokens":
    print("  >>> DEFECT CONFIRMED: Response was abruptly cut off mid-sentence!")
    print("      Client application received HTTP 200, but the user received an incomplete answer.")
else:
    print(f"  Stop reason: {stop_reason}")

# ==============================================================================
# SCENARIO 2: Thinking Tokens Starving Output Content
# ==============================================================================
print_section("2. Thinking Tokens Exhausting Output Quota (Zero-Text Defect)")
print("Goal: Observe what happens when reasoning models consume token budgets during thinking.\n")

thinking_model = os.getenv("ANTHROPIC_THINKING_MODEL", model_name)
try:
    thinking_response = client.messages.create(
        model=thinking_model,
        messages=[{"role": "user", "content": "Explain why distributed transactions fail in microservices in depth."}],
        max_tokens=1025,
        thinking={"type": "enabled", "budget_tokens": 1024}
    )
    visible_text = "".join(b.text for b in thinking_response.content if getattr(b, "type", "") == "text")
    thinking_blocks = [b for b in thinking_response.content if getattr(b, "type", "") == "thinking"]
    print(f"Model Used       : {thinking_model}")
    print(f"Stop Reason      : {thinking_response.stop_reason}")
    print(f"Thinking Blocks  : {len(thinking_blocks)} block(s)")
    print(f"Visible Text     : \"{visible_text[:120]}...\"")
    if (not visible_text or thinking_response.stop_reason == "max_tokens"):
        print("\n[QA DEFECT AUDIT]: Token budget constrained during thinking!")
        print("  Root Cause: In reasoning models with extended thinking, thinking tokens consume")
        print("  max_tokens. If the budget is exhausted during thought generation, visible text is starved!")
except Exception as e:
    print(f"Extended thinking model note ({thinking_model}): {e}")
    print("Demonstrating token starvation with constrained standard budget (max_tokens=10):")
    fallback = client.messages.create(
        model=model_name,
        messages=[{"role": "user", "content": "Explain why distributed transactions fail in microservices."}],
        max_tokens=10
    )
    fallback_text = "".join(b.text for b in fallback.content if hasattr(b, "text"))
    print(f"Stop Reason : {fallback.stop_reason}")
    print(f"Output Text : \"{fallback_text}\"")

# ==============================================================================
# SCENARIO 3: Downstream Data Corruption (Truncated JSON)
# ==============================================================================
print_section("3. Downstream Data Corruption (Truncated JSON)")
print("Goal: Show how silent truncation causes unhandled crashes in downstream services.\n")

json_prompt = (
    "Generate a raw JSON array of 10 common UI automated test failure categories with "
    "fields: id, category, root_cause, mitigation. Output only the JSON array without markdown formatting."
)

truncated_json_response = client.messages.create(
    model=model_name,
    messages=[{"role": "user", "content": json_prompt}],
    max_tokens=70
)

raw_output = "".join(block.text for block in truncated_json_response.content if hasattr(block, "text"))
print(f"Raw Output Received:\n{raw_output}\n")
print(f"Stop Reason: {truncated_json_response.stop_reason}")

try:
    data = json.loads(raw_output)
    print("JSON parsed successfully.")
except json.JSONDecodeError as e:
    print(f"[QA DEFECT AUDIT] Downstream Pipeline Crash: {type(e).__name__}: {e}")
    print("  Root Cause: Closing brackets and trailing fields were never emitted due to token starvation.")

print("\n[SDET Takeaways]:")
print("  1. In automated tests, NEVER assert solely on HTTP 200 or non-empty response text.")
print("  2. Always explicitly assert: `assert response.stop_reason == 'end_turn'`.")
print("     In Anthropic Claude, `stop_reason == 'max_tokens'` signifies truncated output.")
print("  3. Be mindful that extended thinking tokens count towards `max_tokens`. Set adequate budgets")
print("     (at least 2,000–4,000 tokens) when enabling reasoning/thinking.")
print("  4. Workshop Lab Reference: See Lab 01 in 'ai-qa-workshops' for writing automated finish-reason assertions.")
