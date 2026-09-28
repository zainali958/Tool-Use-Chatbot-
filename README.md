# 🛠️ Tool-Use Chatbot (100% free, runs locally)

An LLM agent that decides **when** to call tools — weather, calculator, web search, SQL database —
runs them, handles errors, and answers from the results.

| Piece | Free choice | Key needed? |
|---|---|---|
| LLM | [Ollama](https://ollama.com) (`qwen2.5:3b`) | No |
| Weather | Open-Meteo | No |
| Web search | DuckDuckGo (`ddgs`) | No |
| Database | SQLite (auto-generated sample store) | No |
| UI | Streamlit | No |

## Setup
```bash
# 1. Install Ollama from https://ollama.com, then:
ollama pull qwen2.5:3b        # ~2 GB. Have 16 GB RAM? try qwen2.5:7b or llama3.1:8b

# 2. Python deps
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py            # web UI showing every tool call
python -m chatbot.cli           # terminal chat
python -m pytest -q             # unit tests (no Ollama needed)
python evals.py                 # 20-prompt eval: tool accuracy, answers, latency
OLLAMA_MODEL=qwen2.5:7b python evals.py   # compare models
```

## How it works
```
user -> Agent.run() -> LLM ──(tool_calls?)──┐
           ▲                                │ yes: run_tool() [validated, never raises]
           └──────── tool results ◄─────────┘ no: final answer
```
* `chatbot/tools.py` – tool functions, JSON schemas, safe dispatcher
* `chatbot/agent.py` – the loop, step cap, history trimming
* `evals.py` – measures tool-selection accuracy, answer correctness, errors, latency

## Safety & error handling
* Calculator uses an `ast` whitelist (no `eval`), capped exponents
* SQL: SELECT-only, single statement, read-only connection, 50-row cap
* Tool errors are returned to the model as text so it can retry
* Unknown tools / missing args / bad JSON handled; max 6 steps per turn
* Network timeouts on all HTTP calls

## Ideas to extend
Add a tool (currency, Wikipedia), wrap tools as an MCP server, add approval before risky actions,
stream tokens, or compare several Ollama models on `evals.py` and put the table in this README.
