from ..chat_state import ChatState
from langchain_openai import ChatOpenAI

PROMPT = """
You are revising a draft message based on user feedback. You will be given the previous response and the user feedback. You will need to revise the response taking into account the user's feedback while maintaining accuracy and clarity. Focus specifically on addressing the points raised in the feedback.

Original Request:
{original_request}

User Preferences:
{user_preferences}

Past Revisions:
{past_revisions}

Current Draft:
{current_draft}

User feedback:
{feedback}

Please revise the response taking into account the user's feedback while maintaining accuracy and clarity. Focus specifically on addressing the points raised in the feedback.
"""

def revisor_node(state: ChatState) -> ChatState:
    """Node that creates the initial draft of the user input and generates AI response"""
    state["action_log"].append("Revisor node was invoked.")
    
    # Build user preferences from memories
    user_preferences = ""
    if state.get("memories") and len(state["memories"]) > 0:
        user_preferences = "User Preferences:\n" + "\n".join([f"- {memory}" for memory in state["memories"]]) + "\n"

    # Format past revisions for display
    past_revisions_text = ""
    if state["past_revisions"]:
        for i, revision in enumerate(state["past_revisions"], 1):
            past_revisions_text += f"Round {i}:\n"
            past_revisions_text += f"Feedback: {revision['feedback']}\n"
            past_revisions_text += f"Draft: {revision['draft']}\n\n"

    prompt = PROMPT.format(
        original_request=state["original_request"],
        user_preferences=user_preferences,
        past_revisions=past_revisions_text,
        current_draft=state["current_draft"],
        feedback=state["feedback"]
    )
    
    # Get response from OpenAI
    llm = ChatOpenAI(model="gpt-3.5-turbo", max_tokens=500)
    response = llm.invoke(prompt)
    
    # Extract the response
    ai_response = response.content

    # Update state - store current draft and feedback as a dictionary
    state["past_revisions"].append({
        "draft": state["current_draft"],
        "feedback": state["feedback"]
    })
    state["current_draft"] = ai_response

    return state