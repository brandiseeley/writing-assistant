from ..chat_state import ChatState
from langchain_openai import ChatOpenAI

HUMAN_TEMPLATE = """
You are a writing assistant. You will be given a request and you will need to create a draft of the response. The user has preferences that may or may not be applicable, but consider them if they are relevant to the request.

Original Request:
{original_request}

User Preferences:
{user_preferences}

Please create a draft of the response.
"""

def draft_node(state: ChatState) -> ChatState:
    """Node that creates the initial draft of the user input and generates AI response"""
    state["action_log"].append("Draft node was invoked.")
    
    # Build user preferences from applicable memories
    user_preferences = ""
    if state.get("applicable_memories") and len(state["applicable_memories"]) > 0:
        user_preferences = "User Preferences:\n" + "\n".join([f"- {memory}" for memory in state["applicable_memories"]]) + "\n"
    
    # Get response from OpenAI
    llm = ChatOpenAI(model="gpt-3.5-turbo", max_tokens=500)
    response = llm.invoke(HUMAN_TEMPLATE.format(
        original_request=state["original_request"],
        user_preferences=user_preferences
    ))
    
    # Extract the response
    ai_response = response.content

    # Update state
    state["current_draft"] = ai_response
    
    return state