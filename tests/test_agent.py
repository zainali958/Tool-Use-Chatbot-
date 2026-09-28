"""Agent loop tests with a scripted fake LLM (no Ollama needed)."""
from types import SimpleNamespace as NS
from chatbot.agent import Agent, MAX_STEPS


def call(name, **args):
    return NS(function=NS(name=name, arguments=args))


def reply(content="", calls=None):
    return NS(message=NS(content=content, tool_calls=calls))


class FakeClient:
    def __init__(self, script):
        self.script, self.seen = list(script), []

    def chat(self, model, messages, tools):
        self.seen.append(list(messages))
        return self.script.pop(0) if self.script else reply("done")


def test_direct_answer_no_tools():
    a = Agent(client=FakeClient([reply("Paris")]))
    t = a.run("capital of France?")
    assert t.answer == "Paris" and not t.tool_calls


def test_single_tool_roundtrip():
    c = FakeClient([reply(calls=[call("calculate", expression="6*7")]), reply("It is 42")])
    t = Agent(client=c).run("6*7?")
    assert t.answer == "It is 42" and t.tool_calls[0].result == "42" and t.steps == 2
    assert c.seen[1][-1] == {"role": "tool", "content": "42", "tool_name": "calculate"}


def test_parallel_calls():
    c = FakeClient([reply(calls=[call("calculate", expression="1+1"),
                                 call("calculate", expression="2+2")]), reply("2 and 4")])
    t = Agent(client=c).run("x")
    assert [x.result for x in t.tool_calls] == ["2", "4"]


def test_error_is_fed_back_and_model_retries():
    c = FakeClient([reply(calls=[call("calculate", expression="oops")]),
                    reply(calls=[call("calculate", expression="1+1")]), reply("2")])
    t = Agent(client=c).run("x")
    assert t.tool_calls[0].result.startswith("Error") and t.tool_calls[1].result == "2"


def test_infinite_loop_is_capped():
    c = FakeClient([reply(calls=[call("calculate", expression="1+1")])] * 50)
    t = Agent(client=c).run("x")
    assert t.steps == MAX_STEPS and "limit" in t.answer


def test_memory_persists_and_trims_safely():
    a = Agent(client=FakeClient([]))
    for i in range(40):
        a.run(f"msg {i}")
    assert len(a.history) <= 30 and a.history[0]["role"] == "user"
