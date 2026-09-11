from typing import Annotated, List, Optional

from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict
import operator


class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    summary: Optional[str]
    extracted_memory: Optional[str]
    user_id: Optional[int]
