"""
05_streaming_defects.py
Demonstrates the 4 major defect surfaces of LLM streaming implementations:
1. Mid-stream connection drops and telemetry loss.
2. Silent generation truncation via FinishReason.MAX_TOKENS.
3. Client application crashes on non-text/safety chunks.
4. Structured data tearing when streaming partial JSON.
"""

import sys
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
# SCENARIO 1: Mid-Stream Disconnect & Telemetry Loss (State & Cost Leaks)
# ==============================================================================
print_section("1. Mid-Stream Network Drop & Telemetry Black Hole")
print("Goal: Observe what happens to buffered content and token telemetry when a connection drops.\n")

prompt = "List 5 essential test automation principles with concise explanations."
stream = client.models.generate_content_stream(model=model_name, contents=prompt)

accumulated_buffer = []
final_usage = None

try:
    print("Streaming started:")
    for idx, chunk in enumerate(stream, 1):
        if chunk.text:
            sys.stdout.write(chunk.text)
            sys.stdout.flush()
            accumulated_buffer.append(chunk.text)

        if chunk.usage_metadata:
            final_usage = chunk.usage_metadata

        if idx >= 3:
            print("\n\n>>> [SIMULATED NETWORK DROP] TCP connection reset by peer!")
            raise ConnectionResetError("Connection lost to server mid-stream.")
except ConnectionResetError as e:
    print(f"\n[QA DEFECT AUDIT] Caught expected exception: {e}")
    print(f"  - Chunks successfully received : {len(accumulated_buffer)}")
    print(f"  - Characters buffered          : {sum(len(c) for c in accumulated_buffer)}")
    print(f"  - Usage metadata captured      : {final_usage}")
    print("\n[SDET Takeaways]:")
    print("  1. State Poisoning: If this partial buffer is saved to the chat database,")
    print("     subsequent turns will use incomplete context, degrading model accuracy.")
    print("  2. Billing Black Hole: The LLM provider generated tokens (and billed for them),")
    print("     but because usage_metadata only arrives on completion, the app recorded 0 tokens.")

# ==============================================================================
# SCENARIO 2: Silent Truncation via FinishReason.MAX_TOKENS
# ==============================================================================
print_section("2. Silent Truncation via FinishReason.MAX_TOKENS")
print("Goal: Demonstrate that a stream can fail silently without throwing an exception.\n")

truncation_config = types.GenerateContentConfig(max_output_tokens=300)
stream = client.models.generate_content_stream(
    model=model_name,
    contents="Write an in-depth essay comparing Selenium, Cypress, and Playwright.",
    config=truncation_config
)

last_finish_reason = None
print("Streaming response:")
for chunk in stream:
    if chunk.text:
        sys.stdout.write(chunk.text)
        sys.stdout.flush()
    if chunk.candidates and chunk.candidates[0].finish_reason:
        last_finish_reason = chunk.candidates[0].finish_reason

print(f"\n\n[SDET Takeaways]:")
print(f"  - Stream Loop Finished Without Exception: True")
print(f"  - Candidate Finish Reason: {last_finish_reason}")
if last_finish_reason == types.FinishReason.MAX_TOKENS:
    print("  >>> DEFECT DETECTED: Response was abruptly truncated mid-generation!")
    print("      SDETs must assert finish_reason == STOP. A clean loop exit != full generation.")

# ==============================================================================
# SCENARIO 3: Non-Text Chunks & Type Safety (Defensive Rendering)
# ==============================================================================
print_section("3. Non-Text Chunks & Defensive Stream Rendering")
print("Goal: Test why naive `sys.stdout.write(chunk.text)` crashes client applications.\n")

mock_safety_chunk = types.GenerateContentResponse(
    candidates=[types.Candidate(finish_reason=types.FinishReason.SAFETY)]
)

print("Attempting naive write: `sys.stdout.write(mock_safety_chunk.text)` on empty/safety chunk...")
try:
    sys.stdout.write(mock_safety_chunk.text)
except TypeError as te:
    print(f"  >>> APPLICATION CRASH: {type(te).__name__}: {te}")
    print("\n[SDET Takeaways]:")
    print("  Always guard chunk rendering defensively: `if chunk.text: sys.stdout.write(chunk.text)`")
    print("  Ensure UI tests verify graceful error banners when finish_reason == SAFETY.")

# ==============================================================================
# SCENARIO 4: Structured Data Tearing (Streaming JSON)
# ==============================================================================
print_section("4. Structured Data Tearing (Incomplete JSON Streams)")
print("Goal: Demonstrate why streaming structured outputs requires deferred parsing.\n")

json_stream = client.models.generate_content_stream(
    model=model_name,
    contents="Generate a JSON array of 5 bug reports with keys: id, title, severity.",
    config=types.GenerateContentConfig(response_mime_type="application/json")
)

accumulated_json = ""
for idx, chunk in enumerate(json_stream, 1):
    if chunk.text:
        accumulated_json += chunk.text
    if len(accumulated_json) > 80:
        print("Simulating client-side abort mid-stream...")
        break

print(f"\nAccumulated Incomplete Payload Snippet:\n{accumulated_json[:120]}...\n")
try:
    json.loads(accumulated_json)
    print("JSON parsed successfully.")
except json.JSONDecodeError as je:
    print(f"  >>> PARSING FAILURE: {type(je).__name__}: {je}")
    print("\n[SDET Takeaways]:")
    print("  1. Downstream parsers crash if JSON is parsed incrementally without specialized streaming parsers.")
    print("  2. In microservice pipelines, always defer strict JSON validation until the stream")
    print("     completes with FinishReason.STOP.")
    print("  3. Workshop Lab Reference: See Lab 01 in 'ai-qa-workshops' for writing streaming test assertions.")
