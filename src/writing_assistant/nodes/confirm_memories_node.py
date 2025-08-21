from ..chat_state import ChatState
from ..user_manager import UserManager
from langgraph.types import Command, interrupt
from langgraph.graph import END

def confirm_memories_node(state: ChatState) -> Command:
    """
    Present suggested memories to the user for confirmation.
    This node interrupts the workflow to wait for user input.
    """
    state["action_log"].append("Confirm memories node was invoked.")
    
    # Format suggested memories for display
    memories_text = "\n".join([f"• {memory}" for memory in state["suggested_memories"]])
    
    # Create interrupt for memory confirmation
    result = interrupt({
        "type": "memory_confirmation",
        "suggested_memories": state["suggested_memories"],
    })

    if result['action'] == 'confirm_memories':
        # Use the new_memories from the command result (which contains the user's edits)
        updated_memories = result.get("new_memories", [])
        # Save the updated memories
        UserManager().add_memories(state["user"], updated_memories)

    return Command(goto=END)
