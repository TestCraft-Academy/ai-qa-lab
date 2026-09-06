import sys
from google import genai

client = genai.Client()
model_name = "gemini-3.8-flash"

prompt = "List 10 distinct testing strategies for microservices architectures with explanations."
stream = client.models.generate_content_stream(model=model_name, contents=prompt)

print("Starting stream (will simulate client disconnect after 3 chunks):")
try:
    for idx, chunk in enumerate(stream, 1):
        sys.stdout.write(chunk.text)
        sys.stdout.flush()
        if idx >= 3:
            print("\n\n[SIMULATED FAILURE] Network connection dropped mid-stream!")
            raise ConnectionResetError("Connection lost to server.")
except ConnectionResetError as e:
    print(f"\nCaught expected failure: {e}")
    print("Downstream Impact: Client UI left with dangling text and incomplete state.")