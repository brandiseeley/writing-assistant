from typing import Literal
from langgraph.graph import END
from langgraph.types import interrupt, Command
from ..chat_state import ChatState


def human_approval(state: ChatState) -> Command[Literal[END, "revisor"]]:
    """Node that handles human feedback on the draft"""
    state["action_log"].append("Human feedback node was invoked.")
    user_choice = interrupt(
        {
            "question": "Is this correct?",
            # Surface the output that should be
            # reviewed and approved by the human.
            "llm_output": state["current_draft"]
        }
    )

    action = user_choice.get("action")
    feedback = user_choice.get("feedback")
    
    if action == "approve":
        state["action_log"].append("User approved the draft.")
        return Command(goto=END)
    elif action == "revise":
        state["action_log"].append(f"User requested a revision. Providing feedback: {feedback}")
        return Command(goto="revisor", update={"feedback": feedback, "action_log": state["action_log"]})
    elif action == "reject":
        state["action_log"].append("User rejected the draft.")
        return Command(goto=END)
