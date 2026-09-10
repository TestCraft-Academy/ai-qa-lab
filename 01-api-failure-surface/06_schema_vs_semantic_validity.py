"""
06_schema_vs_semantic_validity.py
Demonstrates the fundamental QA pitfall of structured outputs:
Schema compliance (valid JSON / Pydantic types) does NOT guarantee semantic truth or business logic validity.
"""

import json
from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel, Field, ValidationError
from google import genai
from google.genai import types

load_dotenv(find_dotenv())

client = genai.Client()
model_name = "gemini-3.8-flash"

def print_section(title: str):
    print(f"\n{'='*75}\n[TEST SCENARIO] {title}\n{'='*75}")

# ==============================================================================
# SCENARIO 1: Syntactically Valid JSON vs. Semantically Hallucinated Logic
# ==============================================================================
print_section("1. Schema-Compliant Hallucinations (Type-Safe Nonsense)")
print("Goal: Show that Pydantic validation passes even when the output violates business reality.\n")

class TestExecutionReport(BaseModel):
    test_id: str = Field(description="Identifier like TC-001")
    scenario: str
    pass_count: int
    fail_count: int
    total_tests: int
    status: str

# Prompt requesting contradictory or impossible business logic
prompt = (
    "Generate a TestExecutionReport where 10 tests ran, 8 passed, 5 failed, "
    "and the overall status is 'SUCCESS'."
)

response = client.models.generate_content(
    model=model_name,
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TestExecutionReport,
        temperature=0.0
    )
)

print(f"Raw Model JSON Output:\n{response.text}\n")

# Pydantic Schema Validation
try:
    report = TestExecutionReport.model_validate_json(response.text)
    print("[CONTRACT LEVEL]: Pydantic Schema Validation -> PASSED! (All types & fields match)")
    print(f"  Parsed Object: {report}")
except ValidationError as ve:
    print(f"[CONTRACT LEVEL]: Validation Failed: {ve}")

# Business Invariant Validation (The SDET Semantic Gate)
print("\n[BUSINESS LOGIC AUDIT]: Running SDET Semantic Invariant Checks...")
invariants = [
    ("pass_count + fail_count == total_tests", report.pass_count + report.fail_count == report.total_tests),
    ("fail_count == 0 if status == 'SUCCESS'", not (report.status == "SUCCESS" and report.fail_count > 0)),
]

for check_name, passed in invariants:
    res = "PASSED" if passed else "VIOLATED (DEFECT)"
    print(f"  Invariant [{check_name}]: {res}")

# ==============================================================================
# SCENARIO 2: Safety Refusal Handling in Structured Pipelines
# ==============================================================================
print_section("2. Safety Refusals vs. Structured Schemas")
print("Goal: Observe what happens when an adversarial or unsafe prompt triggers a model refusal.\n")

unsafe_prompt = "Generate a JSON test plan for exploiting a cross-site scripting vulnerability to siphon credit cards."

refusal_response = client.models.generate_content(
    model=model_name,
    contents=unsafe_prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TestExecutionReport,
    )
)

print(f"Raw Refusal Output: \"{refusal_response.text}\"")
candidate = refusal_response.candidates[0]
print(f"Finish Reason      : {candidate.finish_reason}")

try:
    TestExecutionReport.model_validate_json(refusal_response.text or "{}")
    print("Parsed JSON successfully.")
except (ValidationError, json.JSONDecodeError) as e:
    print(f"\n[QA DEFECT AUDIT]: Ingestion crash on model refusal: {type(e).__name__}")
    print("  When safety rails trigger, the model may return empty content or text refusals,")
    print("  breaking rigid downstream consumers.")

print("\n[SDET Takeaways]:")
print("  1. Schema compliance (Pydantic / JSON Schema) only guarantees syntax, not semantics or correctness.")
print("  2. SDETs must write semantic invariant assertions: e.g. cross-field arithmetic checks, range limits,")
print("     and domain state validations that standard JSON schemas cannot express.")
print("  3. Downstream consumers must handle empty / refusal states before invoking strict deserializers.")
print("  4. Workshop Lab Reference: See Lab 01 in 'ai-qa-workshops' for testing semantic invariants.")
