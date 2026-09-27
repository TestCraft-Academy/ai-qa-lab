"""
07_tool_calling_vulnerabilities.py
Demonstrates failure surfaces when LLMs invoke external tools:
Hallucinated arguments, unauthorized boundary breaches, and unhandled tool exceptions.
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
        "type": "function",
        "function": {
            "name": "query_database",
            "description": "Queries an internal database table by record ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "The database table to query."
                    },
                    "record_id": {
                        "type": "integer",
                        "description": "The unique record ID."
                    }
                },
                "required": ["table", "record_id"],
                "additionalProperties": False
            }
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

response = client.chat.completions.create(
    model=model_name,
    messages=messages,
    tools=tools,
    temperature=0.0
)

choice = response.choices[0]

if choice.message.tool_calls:
    for tool_call in choice.message.tool_calls:
        print(f"Emitted Function Name: {tool_call.function.name}")
        print(f"Emitted Raw Arguments: {tool_call.function.arguments}")
        args = json.loads(tool_call.function.arguments)
        
        try:
            tool_output = query_database(**args)
        except Exception as e:
            tool_output = f"Tool Execution Error: {type(e).__name__}: {e}"
            print(f"\n[INTERCEPTED]: Caught tool boundary violation -> {tool_output}")
        
        messages.append(choice.message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": tool_output
        })
    
    # Model receives error message from tool execution and informs user
    follow_up = client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.0
    )
    print("\nModel Output / Final Recovery Message:")
    print(f"\"{follow_up.choices[0].message.content.strip()}\"")
else:
    print(f"Model responded directly without calling tool: \"{choice.message.content}\"")

print("\n[QA DEFECT AUDIT]:")
print("  - The client tool intercepted an unauthorized table query ('confidential_salaries') and negative ID (-99).")
print("  - Rather than crashing the application, the tool raised a PermissionError which was fed back")
print("    to the LLM, allowing it to inform the user gracefully.")

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
    print("  If client code does not intercept tool errors and format them as tool message responses,")
    print("  the entire chat session or agent loop aborts immediately.")

print("\n[SDET Takeaways]:")
print("  1. NEVER assume tool arguments emitted by an LLM are pre-sanitized.")
print("  2. Every tool function must enforce strict runtime validation (parameter bounds, table whitelisting).")
print("  3. Automated test suites must inject adversarial, boundary, and negative inputs to verify")
print("     that tools raise controlled errors rather than executing arbitrary operations.")
print("  4. Tool execution loops must have a circuit breaker (e.g. max 5 tool turns) to prevent infinite loops.")
print("  5. Workshop Lab Reference: See Lab 01 in 'ai-qa-workshops' for testing tool calling agents.")
