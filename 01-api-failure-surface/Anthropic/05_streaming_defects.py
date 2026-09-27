"""
05_streaming_defects.py
Demonstrates the 4 major defect surfaces of LLM streaming implementations:
1. Mid-stream connection drops and telemetry loss.
2. Silent generation truncation via stop_reason == 'max_tokens'.
3. Client application crashes on non-text event chunks.
4. Structured data tearing when streaming partial JSON.
Adapted for Anthropic Claude.
"""

import os
import sys
import json
import anthropic
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

client = anthropic.Anthropic()
model_name = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

def print_section(title: str):
    print(f"\n{'='*75}\n[TEST SCENARIO] {title}\n{'='*75}")

# ==============================================================================
# SCENARIO 1: Mid-Stream Disconnect & Telemetry Loss (State & Cost Leaks)
# ==============================================================================
print_section("1. Mid-Stream Network Drop & Telemetry Black Hole")
print("Goal: Observe what happens to buffered content and token telemetry when a connection drops.\n")

prompt = "List 5 essential test automation principles with concise explanations."
stream = client.messages.create(
    model=model_name,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=500,
    stream=True
)

accumulated_buffer = []
final_usage = None

try:
    print("Streaming started:")
    for idx, event in enumerate(stream, 1):
        if event.type == "content_block_delta" and hasattr(event.delta, "text"):
            sys.stdout.write(event.delta.text)
            sys.stdout.flush()
            accumulated_buffer.append(event.delta.text)

        if event.type == "message_delta" and hasattr(event, "usage"):
            final_usage = event.usage

        if len(accumulated_buffer) >= 3:
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
    print("     but because usage arrives in the terminal message_delta event, the app recorded 0 output tokens.")

# ==============================================================================
# SCENARIO 2: Silent Truncation via stop_reason == 'max_tokens'
# ==============================================================================
print_section("2. Silent Truncation via stop_reason == 'max_tokens'")
print("Goal: Demonstrate that a stream can fail silently without throwing an exception.\n")

stream = client.messages.create(
    model=model_name,
    messages=[{"role": "user", "content": "Write an in-depth essay comparing Selenium, Cypress, and Playwright."}],
    max_tokens=300,
    stream=True
)

last_stop_reason = None
print("Streaming response:")
for event in stream:
    if event.type == "content_block_delta" and hasattr(event.delta, "text"):
        sys.stdout.write(event.delta.text)
        sys.stdout.flush()
    if event.type == "message_delta" and hasattr(event.delta, "stop_reason"):
        last_stop_reason = event.delta.stop_reason

print(f"\n\n[SDET Takeaways]:")
print(f"  - Stream Loop Finished Without Exception: True")
print(f"  - Candidate Stop Reason: {last_stop_reason}")
if last_stop_reason == "max_tokens":
    print("  >>> DEFECT DETECTED: Response was abruptly truncated mid-generation!")
    print("      SDETs must assert stop_reason == 'end_turn'. A clean loop exit != full generation.")

# ==============================================================================
# SCENARIO 3: Non-Text Chunks & Type Safety (Defensive Rendering)
# ==============================================================================
print_section("3. Non-Text Chunks & Defensive Stream Rendering")
print("Goal: Test why naive `sys.stdout.write(event.delta.text)` crashes client applications.\n")

# In Anthropic streaming, event types like message_start and message_stop do not have delta.text
class MockMessageStartEvent:
    type = "message_start"

mock_event = MockMessageStartEvent()

print("Attempting naive write: `sys.stdout.write(mock_event.delta.text)` on message_start event...")
try:
    sys.stdout.write(mock_event.delta.text)
except AttributeError as ae:
    print(f"  >>> APPLICATION CRASH: {type(ae).__name__}: {ae}")
    print("\n[SDET Takeaways]:")
    print("  Always guard chunk rendering defensively: check `if event.type == 'content_block_delta'`")
    print("  Anthropic streams multiple event types (message_start, content_block_start, message_delta) that carry no text.")

# ==============================================================================
# SCENARIO 4: Structured Data Tearing (Streaming JSON)
# ==============================================================================
print_section("4. Structured Data Tearing (Incomplete JSON Streams)")
print("Goal: Demonstrate why streaming structured outputs requires deferred parsing.\n")

json_stream = client.messages.create(
    model=model_name,
    messages=[{"role": "user", "content": "Generate a JSON array of 5 bug reports with keys: id, title, severity. Output only raw JSON."}],
    max_tokens=400,
    stream=True
)

accumulated_json = ""
for event in json_stream:
    if event.type == "content_block_delta" and hasattr(event.delta, "text"):
        accumulated_json += event.delta.text
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
    print("     completes with stop_reason == 'end_turn'.")
    print("  3. Workshop Lab Reference: See Lab 01 in 'ai-qa-workshops' for writing streaming test assertions.")
