from langchain_core.messages import SystemMessage
from app.ai.graph.state import AgentState
from app.ai.llm import get_llm

async def memory_node(state: AgentState):
    messages = state["messages"]
    if len(messages) < 2:
        return {"extracted_memory": None}

    extraction_prompt = """
    Review the following conversation. Extract any lasting facts about the user that would be useful for future conversations.
    Examples: "User's name is X", "User is building an AI chatbot", "User prefers Python".
    
    If there are NO facts to extract, reply exactly with "NONE".
    If there are facts, reply with a single string containing the facts, e.g., "User's name is Koushik. User likes Python.".
    """
    
    conversation_text = ""
    for msg in messages[-6:]:
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            role = "User" if msg.type == "human" else "AI"
            conversation_text += f"{role}: {msg.content}\n"

    prompt_messages = [
        SystemMessage(content=extraction_prompt),
        SystemMessage(content=f"Conversation:\n{conversation_text}")
    ]

    llm = get_llm()
    response = await llm.ainvoke(prompt_messages)
    
    if "NONE" in response.content:
        return {"extracted_memory": None}
        
    print(" Memory extracted in graph. Returning to API to save.")
    return {"extracted_memory": response.content}