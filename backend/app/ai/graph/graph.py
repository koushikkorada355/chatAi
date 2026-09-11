from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.ai.graph.state import AgentState
from app.ai.nodes.chat import chat_node
from app.ai.nodes.summarize import summarize_conversation
from app.ai.nodes.memory import memory_node
from app.ai.tools.tools import all_tools

workflow = StateGraph(AgentState)

workflow.add_node("summarize_node", summarize_conversation)
workflow.add_node("chat_node", chat_node)
workflow.add_node("memory_node", memory_node)

tool_node = ToolNode(all_tools)
workflow.add_node("tools_node", tool_node)

workflow.set_entry_point("summarize_node")
workflow.add_edge("summarize_node", "chat_node")


def route_tools(state: AgentState):
    messages = state.get("messages", [])
    if not messages:
        return "memory_node"

    last_message = messages[-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools_node"
    return "memory_node"


workflow.add_conditional_edges("chat_node", route_tools)
workflow.add_edge("tools_node", "chat_node")
workflow.add_edge("memory_node", END)


def build_app_graph(checkpointer):
    return workflow.compile(checkpointer=checkpointer)