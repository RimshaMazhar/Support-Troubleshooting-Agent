"""Simple interactive CLI to talk to the agent live, before wrapping it in an API."""

from app.agent import get_agent_response

print("ParcelPilot Support Agent (CLI test). Type 'exit' to quit.\n")

while True:
    question = input("You: ").strip()
    if question.lower() == "exit":
        print("Goodbye!")
        break
    if not question:
        continue

    result = get_agent_response(question)
    print(f"[route: {result['route']}]")
    print(f"Bot: {result['answer']}\n")