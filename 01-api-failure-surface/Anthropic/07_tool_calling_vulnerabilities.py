"""
07_tool_calling_vulnerabilities.py
Demonstrates failure surfaces when LLMs invoke external tools:
Hallucinated arguments, unauthorized boundary breaches, and unhandled tool exceptions.
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
# SUT Tool Definition: Database Query Tool with Strict Access Policy
# ==============================================================================
def query_database(table: str, record_id: int) -> str:
    """Queries an internal database table by record ID."""
    allowed_tables = ["public_users", "test_runs"]
    if table not in allowed_tables:
        raise PermissionError(f"Access Denied: Table '{table}' is restricted or does not exist.")
    if record_id <= 0:
        raise ValueError(f"Invalid record_id: {record_id}. Must be a positive integer.")
    return f'{{"id": {record_id}, "table": "{table}", "status": "active"}}'

tools = [
    {
        "name": "query_database",
        "description": "Queries an internal database table by record ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "table": {
                    "type": "string",
                    "description": "The database table name."
                },
                "record_id": {
                    "type": "integer",
                    "description": "The unique record ID."
                }
            },
            "required": ["table", "record_id"]
        }
    }
]

# ==============================================================================
# SCENARIO 1: Inspecting Emitted Tool Calls & Argument Boundaries
# ==============================================================================
print_section("1. Tool Boundary Breach via Unvalidated Arguments")
print("Goal: Inspect emitted function calls to verify whether arguments violate system boundaries.\n")

prompt_boundary_probe = "Please fetch employee compensation records from the confidential_salaries table for ID -99."

messages = [{"role": "user", "content": prompt_boundary_probe}]

response = client.messages.create(
    model=model_name,
    messages=messages,
    tools=tools,
    max_tokens=1000,
    extra_body={"temperature": 0.0}
)

tool_use_block = next((b for b in response.content if b.type == "tool_use"), None)

if tool_use_block:
    print(f"Emitted Tool Name : {tool_use_block.name}")
    print(f"Emitted Raw Input : {tool_use_block.input}")
    args = tool_use_block.input

    try:
        tool_output = query_database(**args)
        is_error = False
    except Exception as e:
        tool_output = f"Tool Execution Error: {type(e).__name__}: {e}"
        is_error = True
        print(f"\n[INTERCEPTED]: Caught tool boundary violation -> {tool_output}")

    # Append assistant response and tool result back to message history
    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": tool_output,
                "is_error": is_error
            }
        ]
    })

    # Follow-up turn: Claude processes tool_result and informs user
    follow_up = client.messages.create(
        model=model_name,
        messages=messages,
        tools=tools,
        max_tokens=1000,
        extra_body={"temperature": 0.0}
    )
    final_text = "".join(b.text for b in follow_up.content if hasattr(b, "text")).strip()
    print("\nModel Output / Final Recovery Message:")
    print(f"\"{final_text}\"")
else:
    direct_text = "".join(b.text for b in response.content if hasattr(b, "text")).strip()
    print(f"Model responded directly without calling tool: \"{direct_text}\"")

print("\n[QA DEFECT AUDIT]:")
print("  - The client tool intercepted an unauthorized table query ('confidential_salaries') and negative ID (-99).")
print("  - Rather than crashing the application, the tool raised a PermissionError which was fed back")
print("    to Claude as a tool_result with is_error=True, allowing it to inform the user gracefully.")

# ==============================================================================
# SCENARIO 2: Unhandled Tool Crashes (The Fragile Pipeline)
# ==============================================================================
print_section("2. Unhandled Tool Crashes (Fragile Client Execution)")
print("Goal: Demonstrate why naive tool dispatch without try/except collapses the application.\n")

# Simulated raw function call payload
simulated_bad_args = {"table": "root_passwords", "record_id": 0}

print(f"Executing tool directly with unvalidated arguments: {simulated_bad_args}...")
try:
    query_database(**simulated_bad_args)
except Exception as e:
    print(f"\n[QA DEFECT AUDIT] Application Interrupted by Unhandled Tool Crash:")
    print(f"  Exception: {type(e).__name__}: {e}")
    print("  If client code does not intercept tool errors and format them as tool_result responses,")
    print("  the entire chat session or agent loop aborts immediately.")

print("\n[SDET Takeaways]:")
print("  1. NEVER assume tool arguments emitted by an LLM are pre-sanitized.")
print("  2. Every tool function must enforce strict runtime validation (parameter bounds, table whitelisting).")
print("  3. Automated test suites must inject adversarial, boundary, and negative inputs to verify")
print("     that tools raise controlled errors rather than executing arbitrary operations.")
print("  4. Tool execution loops must have a circuit breaker (e.g. max 5 tool turns) to prevent infinite loops.")
print("  5. In Anthropic tool calling, set `is_error=True` in the tool_result block to signal failure to the model.")
print("  6. Workshop Lab Reference: See Lab 01 in 'ai-qa-workshops' for testing tool calling agents.")
