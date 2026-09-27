"""
01_token_cost_and_densities.py
Demonstrates how LLM tokenization differs from character/word counts,
and the resulting defect surfaces: silent cost blowouts and context under-provisioning.
"""

from dotenv import load_dotenv, find_dotenv
from google import genai

load_dotenv(find_dotenv())

client = genai.Client()
model_name = "gemini-3.8-flash"

def print_section(title: str):
    print(f"\n{'='*75}\n[TEST SCENARIO] {title}\n{'='*75}")

# ==============================================================================
# SCENARIO 1: Token Density Variance Across Data Modalities
# ==============================================================================
print_section("1. Token Density Variance (English vs. Code vs. JSON)")
print("Goal: Demonstrate why estimating context/cost using character or word counts fails.\n")

samples = {
    "Plain English": "Software testing is the process of evaluating and verifying that a software application does what it is supposed to do.",
    "Dense Code": "def qsort(a): return [] if not a else qsort([x for x in a[1:] if x<a[0]]) + [a[0]] + qsort([x for x in a[1:] if x>=a[0]])",
    "Nested JSON": '{"test_run": {"suite": "api_v1", "cases": [{"id": 1, "status": "PASSED"}, {"id": 2, "status": "FAILED"}]}}',
    "Numeric Table": "| ID | Val1 | Val2 | Val3 |\n| 101 | 42.89 | 91.02 | 14.55 |\n| 102 | 88.11 | 12.04 | 77.30 |",
}

print(f"{'Sample Type':15} | {'Chars':5} | {'Words':5} | {'Tokens':6} | {'Tokens/Word':11} | {'Chars/Token':11}")
print("-" * 65)

for name, text in samples.items():
    count = client.models.count_tokens(model=model_name, contents=text)
    words = max(len(text.split()), 1)
    chars = len(text)
    tokens = count.total_tokens
    print(f"{name:15} | {chars:5} | {words:5} | {tokens:6} | {tokens/words:11.2f} | {chars/tokens:11.2f}")

print("\n[QA DEFECT AUDIT]:")
print("  - Code and JSON have significantly higher tokens-per-word than prose due to punctuation,")
print("    indentation, and multi-symbol operators splitting into multiple individual tokens.")
print("  - Assuming '1 word = 1 token' under-estimates payload size by 30-80% for technical data.")

# ==============================================================================
# SCENARIO 2: Silent Cost & Quota Blowout (Pre-Flight Budget Check)
# ==============================================================================
print_section("2. Silent Cost & Quota Blowout")
print("Goal: Test pre-flight token accounting to prevent rate limit (429) and budget breaches.\n")

# Simulated customer support payload containing raw stack trace
large_stacktrace = (
    "Traceback (most recent call last):\n"
    "  File '/app/handlers/payment.py', line 142, in process_transaction\n"
    "    raise TransactionFailedException(f'Gateway timeout: {error_details}')\n"
) * 50

pre_check = client.models.count_tokens(model=model_name, contents=large_stacktrace)
max_allowed_input_tokens = 500

print(f"Calculated Input Tokens: {pre_check.total_tokens}")
print(f"Strict Ingestion Quota : {max_allowed_input_tokens}")

if pre_check.total_tokens > max_allowed_input_tokens:
    print(f"\n[DEFECT PREVENTED]: Payload exceeds token threshold ({pre_check.total_tokens} > {max_allowed_input_tokens})!")
    print("Pre-flight token guard tripped: Rejected before dispatching expensive LLM request.")
else:
    print("\nPayload within limits. Dispatching request...")

print("\n[SDET Takeaways]:")
print("  1. Never trust word/character counts for rate limit or cost budgeting.")
print("  2. SDETs must enforce pre-flight token counting assertions on large payloads (logs, PDFs, RAG chunks)")
print("     to intercept HTTP 429 quota exhaustion and unexpected billing spikes.")
print("  3. Workshop Lab Reference: See Lab 01 in 'ai-qa-workshops' for implementing client-side token guards.")
