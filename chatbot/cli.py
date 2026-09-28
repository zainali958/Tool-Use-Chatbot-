"""Terminal chat:  python -m chatbot.cli"""
from .agent import Agent, DEFAULT_MODEL


def main() -> None:
    agent = Agent()
    print(f"Tool-use chatbot (model: {DEFAULT_MODEL}). Type 'exit' to quit, 'reset' to clear memory.\n")
    while True:
        try:
            text = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in {"exit", "quit"}:
            break
        if text.lower() == "reset":
            agent.reset(); print("(memory cleared)"); continue
        if not text:
            continue
        turn = agent.run(text)
        for c in turn.tool_calls:
            print(f"  [tool] {c.name}({c.arguments}) -> {c.result[:150]}")
        print(f"bot > {turn.answer}\n")


if __name__ == "__main__":
    main()
