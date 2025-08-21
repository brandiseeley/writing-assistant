from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from .chat_state import ChatState
from .nodes.draft_node import draft_node
from .nodes.feedback_node import human_approval
from .nodes.revisor_node import revisor_node
from .nodes.memory_node import memory_extraction_node
from .nodes.confirm_memories_node import confirm_memories_node

def create_chat_graph():
    """Create a simple LangGraph for chat interactions"""
    
    # Create the graph
    workflow = StateGraph(ChatState)
    
    # Add the nodes
    workflow.add_node("draft", draft_node)
    workflow.add_node("human_feedback", human_approval)
    workflow.add_node("revisor", revisor_node)
    workflow.add_node("memory_extraction", memory_extraction_node)
    workflow.add_node("confirm_memories", confirm_memories_node)

    # Set the entry point
    workflow.set_entry_point("draft")
    
    # Add edges
    workflow.add_edge("draft", "human_feedback")
    workflow.add_edge("revisor", "human_feedback")
    workflow.add_edge("memory_extraction", "confirm_memories")
    workflow.add_edge("confirm_memories", END)
    
    checkpointer = InMemorySaver()
    graph = workflow.compile(checkpointer=checkpointer)

    return graph

def initialize_chat_state() -> ChatState:
    """Initialize a new chat state"""
    return {
        "user": None,
        "messages": [],
        "current_draft": "",
        "past_revisions": [],
        "original_request": "",
        "feedback": "",
        "action_log": [],
        "memories": [],
        "suggested_memories": [],
        "new_memories": []
    }
