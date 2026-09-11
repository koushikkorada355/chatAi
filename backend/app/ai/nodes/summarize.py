from langchain_core.messages import RemoveMessage, SystemMessage
from app.ai.graph.state import AgentState
from app.ai.llm import get_llm

async def summarize_conversation(state: AgentState):
    # 1. Get the current messages
    messages = state["messages"]
    
    # 2. If the conversation is short, do nothing
    if len(messages) <= 6:
        return {}
    
    # 3. If it's long, summarize the older messages
    # We keep the last 4 messages, and summarize everything before them
    old_messages = messages[:-4]
    
    # Create a prompt for the LLM to summarize
    summary_prompt = "Please create a concise summary of the following conversation so far. Focus on key facts and context:\n\n"
    for msg in old_messages:
        role = "User" if msg.type == "human" else "AI"
        # Ignore tool messages for the summary
        if hasattr(msg, 'content') and isinstance(msg.content, str):
            summary_prompt += f"{role}: {msg.content}\n"
        
    # Add the existing summary if it exists
    existing_summary = state.get("summary", "")
    if existing_summary:
        summary_prompt += f"\nExisting Summary:\n{existing_summary}\n"
        summary_prompt += "Please update this summary with the new messages above."

    llm = get_llm()
    response = await llm.ainvoke(summary_prompt)
    new_summary = response.content
    
    # 4. Delete the old messages from the state
    delete_operations = [RemoveMessage(id=m.id) for m in old_messages if hasattr(m, 'id')]
    
    # 5. Add the summary as a new System Message
    summary_message = SystemMessage(content=f"Summary of conversation so far: {new_summary}")
    
    print(f" Trimmed {len(old_messages)} messages into a summary.")
    
    return {
        "messages": delete_operations + [summary_message],
        "summary": new_summary
    }