from langchain_core.messages import BaseMessage

from app.ai.graph.state import AgentState
from app.ai.llm import get_llm
from app.ai.tools.tools import all_tools


def _sanitize_messages(messages):
    cleaned = []

    for message in messages or []:
        if not isinstance(message, BaseMessage):
            continue

        content = getattr(message, "content", None)
        tool_calls = getattr(message, "tool_calls", None) or []

        if content is None:
            continue

        if not isinstance(content, str):
            content = str(content)

        # Old broken checkpoint state may contain empty placeholder messages that
        # are not valid for OpenAI/LangChain payload conversion. Keep tool call
        # messages, but drop empty placeholder messages that would crash the API.
        if not content and not tool_calls and getattr(message, "type", None) not in {"tool", "system"}:
            continue

        cleaned.append(message)

    return cleaned


async def chat_node(state: AgentState):
    """Use LangChain tool-calling normally while sanitizing stale invalid state."""
    llm = get_llm()
    messages = _sanitize_messages(state.get("messages", []))

    if not messages:
        messages = state.get("messages", [])

    llm_with_tools = llm.bind_tools(all_tools)
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}