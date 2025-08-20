from ..chat_state import ChatState
from langchain_openai import ChatOpenAI

PROMPT = """
You are revising a draft message based on user feedback. You will be given the previous response and the user feedback. You will need to revise the response taking into account the user's feedback while maintaining accuracy and clarity. Focus specifically on addressing the points raised in the feedback.

Original Request:
{original_request}

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
    # Add the current user message

    prompt = PROMPT.format(
        original_request=state["original_request"],
        past_revisions=state["past_revisions"],
        current_draft=state["current_draft"],
        feedback=state["feedback"]
    )
    
    # Get response from OpenAI
    llm = ChatOpenAI(model="gpt-3.5-turbo", max_tokens=500)
    response = llm.invoke(prompt)
    
    # Extract the response
    ai_response = response.content

    # Update state
    state["past_revisions"].append(state["current_draft"])
    state["current_draft"] = ai_response

    return state