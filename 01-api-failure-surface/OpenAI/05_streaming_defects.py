"""
05_streaming_defects.py
Demonstrates the 4 major defect surfaces of LLM streaming implementations:
1. Mid-stream connection drops and telemetry loss.
2. Silent generation truncation via finish_reason == 'length'.
3. Client application crashes on non-text/null chunks.
4. Structured data tearing when streaming partial JSON.
Adapted for OpenAI.
"""

import sys
import json
import openai
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

client = openai.OpenAI()
model_name = "gpt-4o"

def print_section(title: str):
    print(f"\n{'='*75}\n[TEST SCENARIO] {title}\n{'='*75}")

# ==============================================================================
# SCENARIO 1: Mid-Stream Disconnect & Telemetry Loss (State & Cost Leaks)
# ==============================================================================
print_section("1. Mid-Stream Network Drop & Telemetry Black Hole")
print("Goal: Observe what happens to buffered content and token telemetry when a connection drops.\n")

prompt = "List 5 essential test automation principles with concise explanations."
stream = client.chat.completions.create(
    model=model_name,
    messages=[{"role": "user", "content": prompt}],
    stream=True,
    stream_options={"include_usage": True}
)

accumulated_buffer = []
final_usage = None

try:
    print("Streaming started:")
    for idx, chunk in enumerate(stream, 1):
        content = chunk.choices[0].delta.content if chunk.choices and chunk.choices[0].delta else None
        if content:
            sys.stdout.write(content)
            sys.stdout.flush()
            accumulated_buffer.append(content)

        if chunk.usage:
            final_usage = chunk.usage

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
    print("     but because usage only arrives in the terminal chunk, the app recorded 0 tokens.")

# ==============================================================================
# SCENARIO 2: Silent Truncation via finish_reason == 'length'
# ==============================================================================
print_section("2. Silent Truncation via finish_reason == 'length'")
print("Goal: Demonstrate that a stream can fail silently without throwing an exception.\n")

stream = client.chat.completions.create(
    model=model_name,
    messages=[{"role": "user", "content": "Write an in-depth essay comparing Selenium, Cypress, and Playwright."}],
    max_tokens=300,
    stream=True
)

last_finish_reason = None
print("Streaming response:")
for chunk in stream:
    if chunk.choices and len(chunk.choices) > 0:
        choice = chunk.choices[0]
        if choice.delta and choice.delta.content:
            sys.stdout.write(choice.delta.content)
            sys.stdout.flush()
        if choice.finish_reason:
            last_finish_reason = choice.finish_reason

print(f"\n\n[SDET Takeaways]:")
print(f"  - Stream Loop Finished Without Exception: True")
print(f"  - Candidate Finish Reason: {last_finish_reason}")
if last_finish_reason == "length":
    print("  >>> DEFECT DETECTED: Response was abruptly truncated mid-generation!")
    print("      SDETs must assert finish_reason == 'stop'. A clean loop exit != full generation.")

# ==============================================================================
# SCENARIO 3: Non-Text Chunks & Type Safety (Defensive Rendering)
# ==============================================================================
print_section("3. Non-Text Chunks & Defensive Stream Rendering")
print("Goal: Test why naive `sys.stdout.write(chunk.choices[0].delta.content)` crashes client applications.\n")

# In OpenAI, the initial delta often has content=None (role announcement) or finish delta has content=None
class MockDelta:
    content = None

class MockChoice:
    delta = MockDelta()

class MockChunk:
    choices = [MockChoice()]

mock_chunk = MockChunk()

print("Attempting naive write: `sys.stdout.write(mock_chunk.choices[0].delta.content)` on empty/role chunk...")
try:
    sys.stdout.write(mock_chunk.choices[0].delta.content)
except TypeError as te:
    print(f"  >>> APPLICATION CRASH: {type(te).__name__}: {te}")
    print("\n[SDET Takeaways]:")
    print("  Always guard chunk rendering defensively: `if chunk.choices[0].delta.content: sys.stdout.write(...)`")
    print("  In OpenAI streaming, role announcements, tool call deltas, and terminal chunks carry null content.")

# ==============================================================================
# SCENARIO 4: Structured Data Tearing (Streaming JSON)
# ==============================================================================
print_section("4. Structured Data Tearing (Incomplete JSON Streams)")
print("Goal: Demonstrate why streaming structured outputs requires deferred parsing.\n")

json_stream = client.chat.completions.create(
    model=model_name,
    messages=[{"role": "user", "content": "Generate a JSON object with a 'bugs' array of 5 bug reports with keys: id, title, severity."}],
    response_format={"type": "json_object"},
    stream=True
)

accumulated_json = ""
for idx, chunk in enumerate(json_stream, 1):
    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
        accumulated_json += chunk.choices[0].delta.content
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
    print("     completes with finish_reason == 'stop'.")
    print("  3. Workshop Lab Reference: See Lab 01 in 'ai-qa-workshops' for writing streaming test assertions.")
