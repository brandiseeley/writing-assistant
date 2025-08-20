from typing import Dict, List, TypedDict, Optional

class ChatState(TypedDict):
    user: str
    messages: List[Dict[str, str]]
    current_draft: str
    past_revisions: List[str]
    original_request: str
    feedback: str
    interrupt_data: Optional[Dict]
    action_log: List[str]