from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver

from .chat_state import ChatState
from .nodes.draft_node import draft_node
from .nodes.human_feedback import human_approval
from .nodes.revisor_node import revisor_node

def create_chat_graph():
    """Create a simple LangGraph for chat interactions"""
    
    # Create the graph
    workflow = StateGraph(ChatState)
    
    # Add the nodes
    workflow.add_node("draft", draft_node)
    workflow.add_node("human_feedback", human_approval)
    workflow.add_node("revisor", revisor_node)

    # Set the entry point
    workflow.set_entry_point("draft")
    
    # Add edges
    workflow.add_edge("draft", "human_feedback")
    workflow.add_edge("revisor", "human_feedback")
    
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
        "interrupt_data": None,
        "action_log": [],
        "memories": []
    }
