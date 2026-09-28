"""Evaluate tool selection & answers:  python evals.py [model]"""
import json
import statistics
import sys

from chatbot.agent import Agent, DEFAULT_MODEL

# (prompt, expected set of tools, substring expected in answer or None)
CASES = [
    ("What is 15% of 2340?", {"calculate"}, "351"),
    ("Compute sqrt(144) * 3", {"calculate"}, "36"),
    ("What is 987654 divided by 12?", {"calculate"}, "82304.5"),
    ("What's the weather in Islamabad right now?", {"get_weather"}, None),
    ("Compare the weather in Karachi and Lahore", {"get_weather"}, None),
    ("Is it raining in London?", {"get_weather"}, None),
    ("How many customers are in the database?", {"query_database"}, "6"),
    ("How many orders are there in total?", {"query_database"}, "60"),
    ("Which product category has the most products?", {"query_database"}, None),
    ("List the customers from Islamabad", {"query_database"}, "Ayesha"),
    ("What is the price of the most expensive product?", {"query_database"}, "950"),
    ("Search the web for the latest Python release", {"search_web"}, None),
    ("Who is the current CEO of NVIDIA?", {"search_web"}, None),
    ("Find recent news about open-source LLMs", {"search_web"}, None),
    ("Hi! How are you?", set(), None),
    ("What is the capital of France?", set(), "Paris"),
    ("Write a one-line joke about robots", set(), None),
    ("Explain what an API is in one sentence", set(), None),
    ("What's the total value of all orders (quantity x price)?", {"query_database"}, None),
    ("Find Japan's population and divide it by 47", {"search_web", "calculate"}, None),
]


def main() -> None:
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL
    rows = []
    for prompt, expected, needle in CASES:
        agent = Agent(model=model)
        try:
            t = agent.run(prompt)
            used = {c.name for c in t.tool_calls}
            errors = sum(c.result.startswith("Error") for c in t.tool_calls)
            rows.append({"prompt": prompt, "expected": sorted(expected), "used": sorted(used),
                         "tool_ok": used == expected,
                         "answer_ok": True if needle is None else needle.lower() in t.answer.lower(),
                         "tool_errors": errors, "seconds": round(t.seconds, 1), "answer": t.answer})
        except Exception as exc:  # noqa: BLE001
            rows.append({"prompt": prompt, "expected": sorted(expected), "used": [],
                         "tool_ok": False, "answer_ok": False, "tool_errors": 0,
                         "seconds": 0, "answer": f"CRASH: {exc}"})
        r = rows[-1]
        print(f"{'PASS' if r['tool_ok'] and r['answer_ok'] else 'FAIL'}  {prompt}  -> {r['used']}")
    n = len(rows)
    print("\n=== RESULTS ===")
    print(f"Model:                   {model}")
    print(f"Tool selection accuracy: {sum(r['tool_ok'] for r in rows) / n:.0%}")
    print(f"Answer correctness:      {sum(r['answer_ok'] for r in rows) / n:.0%}")
    print(f"Tool errors:             {sum(r['tool_errors'] for r in rows)}")
    print(f"Median latency:          {statistics.median(r['seconds'] for r in rows):.1f}s")
    with open("eval_results.json", "w") as f:
        json.dump(rows, f, indent=2)
    print("Saved eval_results.json")


if __name__ == "__main__":
    main()
