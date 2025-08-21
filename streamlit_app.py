import streamlit as st
import sys
import os
import dotenv
import uuid
from langgraph.types import Command
from uuid import uuid4

dotenv.load_dotenv()

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from writing_assistant.chat_graph import create_chat_graph, initialize_chat_state
from writing_assistant.user_manager import UserManager


def add_new_message(role, content, type=None):
    """Handle new message."""
    st.session_state.messages.append({"role": role, "content": content, "message_type": type})

def display_draft_message(message, message_index, column):
    """Display a draft message with approve/reset action buttons."""
    with column.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Add action buttons only for draft messages (not status messages)
        if message.get("message_type") == "draft" and message_index == len(st.session_state.messages) - 1:
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                if st.button("Approve", key=f"approve_{message_index}"):
                    handle_draft_approval()
            with col2:
                if st.button("Reset", key=f"reset_{message_index}"):
                    handle_draft_reset()


def display_user_message(message, column):
    """Display a user message (normal or feedback)."""
    with column.chat_message(message["role"]):
        st.markdown(message["content"])

def display_memory_message(message, column):
    """Display and ask for confirmation of new memories from the assistant."""
    memories = message["content"]
    with column.chat_message("assistant"):
        st.write("I've deduced the following memories:")
        for i, memory in enumerate(memories):
            st.write(f"{i+1}. {memory}")
            if st.button(f"Save Memory {i+1}", key=f"save_memory_{i}"):
                st.session_state.current_state["action_log"].append(f"User confirmed memory #{i+1}")
                st.session_state.current_state["new_memories"].append(memory)
                st.rerun()
            if st.button(f"Ignore Memory {i+1}", key=f"ignore_memory_{i}"):
                st.session_state.current_state["action_log"].append(f"User ignored memory #{i+1}")
                st.rerun()
        if st.button("Save Memories"):
            st.session_state.current_state["action_log"].append(f"User confirmed memories. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
            result = st.session_state.chat_graph.invoke(Command(resume={"action": "confirm_memories", "new_memories": st.session_state.current_state["new_memories"]}), config=st.session_state.config)
            st.session_state.current_state = result
            add_new_message("assistant", "Memories saved.", "status")
            st.rerun()


def handle_draft_approval():
    """Handle draft approval action."""
    add_new_message("user", "Draft approved", "draft")
    st.session_state.current_state["action_log"].append(f"User approved draft. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
    st.session_state.feedback_mode = False
    result = st.session_state.chat_graph.invoke(Command(resume={"action": "approve", "feedback": ""}), config=st.session_state.config)
    st.session_state.current_state = result
    if len(st.session_state.current_state["past_revisions"]) > 0:
        add_new_message("assistant", "Checking for new memories...", "status")
        handle_memory_confirmation()
    st.rerun()


def handle_draft_reset():
    """Handle draft reset action."""
    st.session_state.current_state["action_log"].append(f"User requested reset. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
    st.session_state.feedback_mode = False
    result = st.session_state.chat_graph.invoke(Command(resume={"action": "reset"}), config=st.session_state.config)
    st.session_state.current_state = result
    st.rerun()


def initialize_session_state():
    """Initialize all session state variables."""
    if "chat_graph" not in st.session_state:
        st.session_state.chat_graph = create_chat_graph()
    if "config" not in st.session_state:
        st.session_state.config = {"configurable": {"thread_id": uuid.uuid4()}}
    if "current_state" not in st.session_state:
        st.session_state.current_state = initialize_chat_state()
        st.session_state.current_state["action_log"] = [f'Graph was initialized. ConfigID: {str(st.session_state.config["configurable"]["thread_id"])[:6]}...']
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "feedback_mode" not in st.session_state:
        st.session_state.feedback_mode = False


def handle_feedback_mode(new_message):
    """Handle feedback mode interaction."""
    add_new_message("user", f"Feedback: {new_message}")
    st.session_state.current_state["action_log"].append(f"User provided feedback: {new_message}")
    
    try:
        result = st.session_state.chat_graph.invoke(
            Command(resume={"action": "revise", "feedback": new_message}), 
            config=st.session_state.config
        )
        st.session_state.current_state = result
        
        if result.get("current_draft"):
            add_new_message("assistant", result["current_draft"], "draft")
        
        st.rerun()
    except Exception as e:
        st.error(f"Error processing feedback: {e}")


def handle_normal_mode(new_message):
    """Handle normal chat mode interaction."""
    add_new_message("user", new_message)
    st.session_state.current_state["action_log"].append("User sent a request.")
    st.session_state.current_state["original_request"] = new_message
    
    try:
        result = st.session_state.chat_graph.invoke(st.session_state.current_state, config=st.session_state.config)
        st.session_state.current_state = result
        
        if result.get("current_draft"):
            add_new_message("assistant", result["current_draft"], "draft")
            st.session_state.feedback_mode = True
        
        st.rerun()
    except Exception as e:
        st.error(f"Error: {e}")


def handle_memory_confirmation():
    """Handle memory confirmation interrupt."""
    interrupt_obj = st.session_state.current_state["__interrupt__"][0]
    
    if hasattr(interrupt_obj, 'value'):
        interrupt_data = interrupt_obj.value
    else:
        interrupt_data = interrupt_obj

    add_new_message("assistant", interrupt_data['suggested_memories'], "memory")  


def setup_chat_interface(column):
    """Setup and handle the chat interface."""
    column.header("Chat")

    # Display chat messages from history on app rerun
    for i, message in enumerate(st.session_state.messages):
        if message["role"] == "assistant" and message.get("message_type") == "draft":
            display_draft_message(message, i, column)
        elif message["role"] == "assistant" and message.get("message_type") == "memory":
            display_memory_message(message, column)
        else:
            display_user_message(message, column)

    # Show feedback mode indicator
    if st.session_state.feedback_mode:
        column.info("📝 Feedback mode - provide feedback on the draft above")

    # Set placeholder text based on mode
    placeholder_text = "Provide feedback on the draft..." if st.session_state.feedback_mode else "Send a message..."
    new_message = column.chat_input(placeholder_text)

    if new_message:
        if st.session_state.feedback_mode:
            handle_feedback_mode(new_message)
        else:
            handle_normal_mode(new_message)


def setup_sidebar():
    """Setup the sidebar with user selection and state display."""
    # User selection
    st.sidebar.header("User Selection")
    available_users = user_manager.get_all_users()
    user_options = ["New User"] + available_users
    selected_user = st.sidebar.selectbox("Select User:", user_options)

    # Update current state with selected user and trigger rerun if changed
    if selected_user != st.session_state.current_state["user"]:
        st.session_state.current_state["user"] = selected_user
        
        # Fetch and add user memories to state
        if selected_user != "New User":
            memories = user_manager.get_memories(selected_user)
            st.session_state.current_state["memories"] = memories
        else:
            st.session_state.current_state["memories"] = []
        
        st.rerun()

    # Display current memories
    st.sidebar.header("Current Memories")
    if st.session_state.current_state["memories"]:
        for i, memory in enumerate(st.session_state.current_state["memories"], 1):
            st.sidebar.write(f"{i}. {memory}")
    else:
        st.sidebar.write("No memories stored yet.")

    # Display action log
    st.sidebar.header("Action Log")
    for action in st.session_state.current_state["action_log"]:
        st.sidebar.write(action)

    # Display graph
    graph = create_chat_graph()
    img_bytes = graph.get_graph().draw_mermaid_png()  
    st.sidebar.image(img_bytes)


def setup_page_layout():
    """Setup the main page layout."""
    st.set_page_config(page_title="Writing Assistant", page_icon="📝", layout="wide")
    st.title("📝 Writing Assistant")
    return st.columns(2)


# Initialize user manager
user_manager = UserManager()

# Setup page layout
left_column, right_column = setup_page_layout()

# Check for API key
if not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️ Please set your OPENAI_API_KEY environment variable")
    st.stop()

# Initialize session state
initialize_session_state()

# Setup chat interface
setup_chat_interface(left_column)

# Display state - RIGHT COLUMN
right_column.header("Current State")
right_column.json(st.session_state.current_state)

# Setup sidebar
setup_sidebar()
