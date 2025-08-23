from ..chat_state import ChatState
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

SYSTEM_TEMPLATE = """
You are ContextCraft, revising a draft based on user feedback. Your goal is to implement the feedback precisely while preserving accuracy, clarity, and the user's preferred style.

Revise using this policy:

- Address each explicit point in the feedback. If feedback conflicts with the Original Request, prioritize the request unless the user overrides it clearly.
- Apply relevant User Preferences and patterns from the conversation history when they help.
- Do not add new claims or details that weren't in the request/draft unless the user explicitly asked for them or they are trivial formatting additions (e.g., subject line).
- Keep the good parts; focus edits where needed (tone, structure, concision, emphasis).
- If the user asked for length/tone/format changes, satisfy them.
- Output only the revised draft (no explanations or change logs).

User Preferences (may be empty):
{user_preferences}

Output only the revised draft. No commentary, no labels.

# Examples (for edit precision)

Example A
**Original Request:**

"Write a brief internal note explaining the outage and next steps."

**User Preferences:**

Internal notes: concise, factual, no blame; end with clear next steps

**Current Draft:**

We experienced an outage due to a database failover. We're investigating and will follow up later.

**User Feedback:**

Make it more specific, keep it under 80 words, add next steps, and avoid passive voice.

**Revised Draft:**

We had a 27-minute outage caused by a failed primary-to-replica failover. We restored service at 10:42 PT and confirmed data integrity. Next steps: finalize root cause analysis by EOD, add a failover health check, and run a failover drill this week.

Example B
**Original Request:**

"Email the customer about the delayed shipment; keep a respectful tone and provide options."

**User Preferences:**

Customer emails: empathetic, solution-forward, no overpromising; include a clear CTA

**Current Draft:**

Hi Alex,
Your order is delayed. We're sorry about this and are trying to ship it soon.

**User Feedback:**

Make it more formal, give two concrete options, and add a subject line.

**Revised Draft:**

Subject: Update on Your Order and Next Steps
Hi Alex,
Thank you for your patience. Your order is running behind schedule due to a carrier delay. We can:

Ship via expedited service at no additional cost (arrives 2-3 days sooner), or
Maintain standard shipping (no action needed). Please reply with your preference, and we'll proceed immediately. Sincerely, [Your Name] 
"""

def revisor_node(state: ChatState) -> ChatState:
    """Node that creates the initial draft of the user input and generates AI response"""
    state["action_log"].append("Revisor node was invoked.")
    
    # Build user preferences from memories
    user_preferences = ""
    if state.get("memories") and len(state["memories"]) > 0:
        user_preferences = "User Preferences:\n" + "\n".join([f"- {memory}" for memory in state["memories"]]) + "\n"

    # Build conversation history from past revisions
    messages = []
    
    # Add system message
    system_message = SystemMessage(content=SYSTEM_TEMPLATE.format(user_preferences=user_preferences))
    messages.append(system_message)
    
    # Add original request as first user message
    original_request_message = HumanMessage(content=state["original_request"])
    messages.append(original_request_message)
    
    # Add conversation history from past revisions
    if state["past_revisions"]:
        for revision in state["past_revisions"]:
            # Add the draft as assistant message
            assistant_message = AIMessage(content=revision["draft"])
            messages.append(assistant_message)
            # Add the feedback as user message
            feedback_message = HumanMessage(content=revision["feedback"])
            messages.append(feedback_message)
    
    # Add current draft as assistant message
    current_draft_message = AIMessage(content=state["current_draft"])
    messages.append(current_draft_message)
    
    # Add current feedback as user message
    feedback_message = HumanMessage(content=state["feedback"])
    messages.append(feedback_message)

    # Get response from OpenAI using conversation history
    llm = ChatOpenAI(model="gpt-3.5-turbo", max_tokens=500)
    response = llm.invoke(messages)
    
    # Extract the response
    ai_response = response.content

    # Update state - store current draft and feedback as a dictionary
    state["past_revisions"].append({
        "draft": state["current_draft"],
        "feedback": state["feedback"]
    })
    state["current_draft"] = ai_response

    return state