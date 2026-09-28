"""Web UI:  streamlit run app.py"""
import streamlit as st

from chatbot.agent import Agent, DEFAULT_MODEL

st.set_page_config(page_title="Tool-Use Chatbot", page_icon="🛠️")
st.title("🛠️ Tool-Use Chatbot")
st.caption("Weather · Calculator · Web search · SQL database — 100% free & local")

with st.sidebar:
    model = st.text_input("Ollama model", DEFAULT_MODEL)
    if st.button("Clear conversation"):
        st.session_state.clear()
        st.rerun()
    st.markdown("**Try:**\n- Weather in Lahore vs Karachi?\n- Total revenue per category?\n"
                "- What's 15% of 2,340?\n- Latest news about Python 3.14")

if "agent" not in st.session_state or st.session_state.get("model") != model:
    st.session_state.agent, st.session_state.model = Agent(model=model), model
    st.session_state.log = []

for m in st.session_state.log:
    with st.chat_message(m["role"]):
        st.markdown(m["text"])
        for c in m.get("tools", []):
            with st.expander(f"🔧 {c.name}({c.arguments}) — {c.seconds:.1f}s"):
                st.code(c.result)

if prompt := st.chat_input("Ask something..."):
    st.session_state.log.append({"role": "user", "text": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"), st.spinner("Thinking..."):
        try:
            turn = st.session_state.agent.run(prompt)
            text, tools = turn.answer, turn.tool_calls
        except Exception as exc:  # e.g. Ollama not running
            text, tools = f"⚠️ {exc}\n\nIs Ollama running? Try `ollama serve`.", []
        st.markdown(text)
        for c in tools:
            with st.expander(f"🔧 {c.name}({c.arguments}) — {c.seconds:.1f}s"):
                st.code(c.result)
    st.session_state.log.append({"role": "assistant", "text": text, "tools": tools})
