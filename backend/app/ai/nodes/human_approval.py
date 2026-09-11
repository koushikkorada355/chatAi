import logging

from langchain_core.messages import ToolMessage
from langgraph.types import interrupt

from app.ai.graph.state import AgentState

logger = logging.getLogger(__name__)


def _tool_name_from_last_message(last_message):
    if last_message is None:
        return "tool"

    tool_calls = getattr(last_message, "tool_calls", None) or []
    if not tool_calls:
        return "tool"

    first_call = tool_calls[0]
    if isinstance(first_call, dict):
        return first_call.get("name") or "tool"

    return "tool"


async def human_approval_node(state: AgentState):
    messages = state.get("messages") or []
    last_message = messages[-1] if messages else None
    tool_name = _tool_name_from_last_message(last_message)

    interrupt_payload = {
        "message": f"Do you approve the execution of {tool_name}?",
        "tool": tool_name,
    }

    logger.info("Pausing graph for human approval: %s", interrupt_payload)
    user_decision = interrupt(interrupt_payload)

    if user_decision is None:
        return {
            "human_approval": None,
            "approval_pending": True,
        }

    if user_decision is False:
        return {
            "messages": [
                ToolMessage(content="The user rejected this tool execution.", tool_call_id="rejected")
            ],
            "human_approval": False,
            "approval_pending": False,
        }

    return {
        "human_approval": True,
        "approval_pending": False,
    }