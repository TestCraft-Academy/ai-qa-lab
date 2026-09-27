"""
03_temperature_and_variance.py
Demonstrates the core testing problem in AI: stochastic non-determinism,
how temperature flattens logit distributions, and why 'it passed once' is meaningless in QA.
Adapted for Anthropic Claude.
"""

import os
import anthropic
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

client = anthropic.Anthropic()
model_name = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

def print_section(title: str):
    print(f"\n{'='*75}\n[TEST SCENARIO] {title}\n{'='*75}")

# ==============================================================================
# SCENARIO 1: Multi-Run Output Stability Across Temperatures
# ==============================================================================
print_section("1. Response Variance Across Temperatures (0.0 vs. 0.5 vs. 1.0)")
print("Goal: Observe how sampling temperature introduces variance and unpredictability.\n")
print("Note: Anthropic Claude accepts temperature values in the range [0.0, 1.0].\n")

prompt = "Define the term 'Regression Test' in exactly one punchy sentence."

for temp in [0.0, 0.5, 1.0]:
    print(f"\n--- Testing at Temperature: {temp:.1f} ---")
    responses = []
    for run_idx in range(1, 4):
        resp = client.messages.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            extra_body={"temperature": temp}
        )
        text = "".join(b.text for b in resp.content if hasattr(b, "text")).strip()
        responses.append(text)
        print(f"  Run {run_idx}: {text}")
    
    unique_count = len(set(responses))
    print(f"  --> Unique outputs across 3 runs: {unique_count} of 3")

# ==============================================================================
# SCENARIO 2: The 'It Passed Once' Trap (Flaky Assertion Simulation)
# ==============================================================================
print_section("2. The 'It Passed Once' Flaky Test Trap")
print("Goal: Demonstrate how an assertion passes intermittently at moderate temperatures.\n")

test_prompt = "Classify this bug severity (Low, Medium, High, Critical): 'Database password logged in clear text to stdout.'"
required_keyword = "critical"

temp_to_test = 1.0
iterations = 5
passed = 0

print(f"Running assertion: assert '{required_keyword}' in response.lower()")
print(f"Configuration     : temperature = {temp_to_test}, iterations = {iterations}\n")

for i in range(1, iterations + 1):
    res = client.messages.create(
        model=model_name,
        messages=[{"role": "user", "content": test_prompt}],
        max_tokens=100,
        extra_body={"temperature": temp_to_test}
    )
    output = "".join(b.text for b in res.content if hasattr(b, "text")).strip()
    is_pass = required_keyword in output.lower()
    if is_pass:
        passed += 1
    status = "PASSED" if is_pass else "FAILED"
    print(f"  Run {i:02d} | [{status}] -> \"{output[:70]}\"")

print(f"\n[QA DEFECT AUDIT]:")
print(f"  - Flakiness Ratio: {passed}/{iterations} passed ({(passed/iterations)*100:.1f}%)")
if passed < iterations:
    print("  >>> FLAKY TEST DETECTED: A single test run in CI gives false confidence.")
    print("      If this test ran once on a PR, it could pass by random chance or fail on re-run.")

print("\n[SDET Takeaways]:")
print("  1. Deterministic Tasks (classification, extraction, JSON) must enforce `temperature=0.0` in production.")
print("  2. In automated testing of stochastic pipelines, single-run assertions (`assert X`) are anti-patterns.")
print("  3. QA must use Pass@k or statistical distribution testing (e.g. Wilson score intervals across N runs).")
print("  4. Remember that Anthropic enforces a temperature range of 0.0 to 1.0.")
print("  5. Workshop Lab Reference: See Lab 04 in 'ai-qa-workshops' for calculating confidence intervals on pass rates.")
