from typing import Dict, List, TypedDict

class ChatState(TypedDict):
    user: str
    messages: List[Dict[str, str]]
    current_draft: str
    past_revisions: List[Dict[str, str]]
    original_request: str
    feedback: str
    action_log: List[str]
    memories: List[str]
    suggested_memories: List[str]
    new_memories: List[str]