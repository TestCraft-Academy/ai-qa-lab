"""
03_temperature_and_variance.py
Demonstrates the core testing problem in AI: stochastic non-determinism,
how temperature flattens logit distributions, and why 'it passed once' is meaningless in QA.
Adapted for OpenAI.
"""

import os
import openai
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

client = openai.OpenAI()
model_name = os.getenv("OPENAI_MODEL", "gpt-4o")

def print_section(title: str):
    print(f"\n{'='*75}\n[TEST SCENARIO] {title}\n{'='*75}")

# ==============================================================================
# SCENARIO 1: Multi-Run Output Stability Across Temperatures
# ==============================================================================
print_section("1. Response Variance Across Temperatures (0.0 vs. 1.0 vs. 2.0)")
print("Goal: Observe how sampling temperature introduces variance and unpredictability.\n")

prompt = "Define the term 'Regression Test' in exactly one punchy sentence."

for temp in [0.0, 1.0, 2.0]:
    print(f"\n--- Testing at Temperature: {temp:.1f} ---")
    responses = []
    for run_idx in range(1, 4):
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temp,
            max_tokens=60
        )
        text = resp.choices[0].message.content.strip()
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
    res = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": test_prompt}],
        temperature=temp_to_test,
        max_tokens=60
    )
    output = res.choices[0].message.content.strip()
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
print("  4. Workshop Lab Reference: See Lab 04 in 'ai-qa-workshops' for calculating confidence intervals on pass rates.")
