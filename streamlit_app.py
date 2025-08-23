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
        
        # Show memories used in this draft
        if st.session_state.current_state.get("applicable_memories"):
            with st.expander("Memories Used in This Draft", expanded=False):
                memories = st.session_state.current_state["applicable_memories"]
                if memories:
                    for i, memory in enumerate(memories, 1):
                        st.write(f"{i}. {memory}")
                else:
                    st.write("No specific memories were used for this draft.")
        
        # Add action buttons only for draft messages (not status messages)
        if message.get("message_type") == "draft" and message_index == len(st.session_state.messages) - 1:
            col1, col2, _, _, _, _, _, _ = st.columns(8)
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

def display_memory_message(message, message_index, column):
    """Display and ask for confirmation of new memories from the assistant."""
    # Initialize editing state if not exists
    if "editing_memory" not in st.session_state:
        st.session_state.editing_memory = None
    
    # Use current suggested_memories from session state for the actual data
    memories = st.session_state.current_state["suggested_memories"]
    with column.chat_message("assistant"):
        st.write("I've deduced the following memories:")
        for i, memory in enumerate(memories):
            # Only show buttons for the last memory message
            if message_index == len(st.session_state.messages) - 1:
                # Check if this memory is being edited
                if st.session_state.editing_memory == i:
                    # Edit mode - show text input and save/cancel buttons
                    edited_memory = st.text_area(
                        f"Edit memory {i+1}:", 
                        value=memory, 
                        key=f"edit_memory_input_{i}",
                        height=100
                    )
                    
                    col1, col2, _, _, _, _, _, _ = st.columns(8)
                    with col1:
                        if st.button("Save", key=f"save_memory_{i}"):
                            # Update the memory in session state
                            st.session_state.current_state["suggested_memories"][i] = edited_memory
                            st.session_state.current_state["action_log"].append(f"User edited memory #{i+1}")
                            st.session_state.editing_memory = None
                            
                            # Remove the old memory message and recreate it with updated state
                            st.session_state.messages.pop()
                            add_new_message("assistant", st.session_state.current_state["suggested_memories"], "memory")
                            st.rerun()
                    
                    with col2:
                        if st.button("Cancel", key=f"cancel_memory_{i}"):
                            st.session_state.editing_memory = None
                            st.rerun()
                else:
                    # Display mode - show memory text and action buttons
                    st.write(f"{i+1}. {memory}")
                    
                    col1, col2, _, _, _, _, _, _ = st.columns(8)
                    with col1:
                        if st.button(f"Edit", key=f"edit_memory_{i}"):
                            st.session_state.editing_memory = i
                            st.rerun()
                    
                    with col2:
                        if st.button(f"Delete", key=f"delete_memory_{i}"):
                            # Remove from suggested memories list using index
                            if i < len(st.session_state.current_state["suggested_memories"]):
                                st.session_state.current_state["suggested_memories"].pop(i)
                                st.session_state.current_state["action_log"].append(f"User deleted memory #{i+1}")
                                
                                # Reset editing state if we were editing a memory after the deleted one
                                if st.session_state.editing_memory is not None and st.session_state.editing_memory >= i:
                                    st.session_state.editing_memory = None
                                
                                # Remove the old memory message and recreate it with updated state
                                st.session_state.messages.pop()
                                add_new_message("assistant", st.session_state.current_state["suggested_memories"], "memory")
                                st.rerun()
            else:
                # For older messages, just display the memory without buttons
                st.write(f"{i+1}. {memory}")
        
        # Only show the save memories button if this is the last message and no memory is being edited
        if message_index == len(st.session_state.messages) - 1 and st.session_state.editing_memory is None:
            if st.button("Save Memories"):
                st.session_state.current_state["action_log"].append(f"User confirmed memories. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
                # Store the memories the user kept
                saved_memories = st.session_state.current_state["suggested_memories"].copy()
                # Pass the user's modified memories to the graph
                st.session_state.chat_graph.invoke(Command(resume={"action": "confirm_memories", "new_memories": saved_memories}), config=st.session_state.config)
                # Keep the saved memories in suggested_memories for display
                st.session_state.current_state["suggested_memories"] = saved_memories
                add_new_message("assistant", "Memories saved.", "status")
                # Job completed after saving memories
                st.session_state.job_completed = True
                st.rerun()


def handle_draft_approval():
    """Handle draft approval action."""
    st.session_state.current_state["action_log"].append(f"User approved draft. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
    st.session_state.feedback_mode = False
    result = st.session_state.chat_graph.invoke(Command(resume={"action": "approve", "feedback": ""}), config=st.session_state.config)
    st.session_state.current_state = result
    # Only check for memories if there are past revisions AND no memory message already exists
    if len(st.session_state.current_state["past_revisions"]) > 0 and not any(msg.get("message_type") == "memory" for msg in st.session_state.messages):
        add_new_message("assistant", "Approved.Checking for new memories...", "status")
        handle_memory_confirmation()
    else:
        # Job completed without memories to extract
        st.session_state.job_completed = True
    st.rerun()


def handle_draft_reset():
    """Handle draft reset action."""
    st.session_state.current_state["action_log"].append(f"User requested reset. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
    st.session_state.feedback_mode = False
    result = st.session_state.chat_graph.invoke(Command(resume={"action": "reset"}), config=st.session_state.config)
    st.session_state.current_state = result
    st.session_state.messages = []
    st.rerun()


def handle_new_job():
    """Handle new job action - keep user but reset messages and drafts."""
    # Use persisted user if available, otherwise use current user
    current_user = st.session_state.persisted_user if st.session_state.persisted_user != "None Selected" else st.session_state.current_state["user"]
    current_memories = st.session_state.current_state["memories"].copy()
    
    # Reset session state for new job
    st.session_state.messages = []
    st.session_state.feedback_mode = False
    st.session_state.job_completed = False
    st.session_state.editing_memory = None
    st.session_state.config = {"configurable": {"thread_id": uuid.uuid4()}}
    
    # Initialize new state but keep user and memories
    st.session_state.current_state = initialize_chat_state()
    st.session_state.current_state["user"] = current_user
    st.session_state.current_state["memories"] = current_memories
    st.session_state.current_state["action_log"] = [f'New job started. ConfigID: {str(st.session_state.config["configurable"]["thread_id"])[:6]}...']
    
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
    if "job_completed" not in st.session_state:
        st.session_state.job_completed = False
    if "editing_memory" not in st.session_state:
        st.session_state.editing_memory = None
    if "persisted_user" not in st.session_state:
        st.session_state.persisted_user = "None Selected"
    

def handle_feedback_mode(new_message):
    """Handle feedback mode interaction."""
    add_new_message("user", f"Feedback: {new_message}")
    display_user_message({'role': 'user', 'content': f"Feedback: {new_message}"}, st)
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
    display_user_message({'role': 'user', 'content': new_message}, st)
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
    display_user_message({'role': 'assistant', 'content': "Approved. Checking for new memories..."}, st)
    interrupt_obj = st.session_state.current_state["__interrupt__"][0]
    
    if hasattr(interrupt_obj, 'value'):
        interrupt_data = interrupt_obj.value
    else:
        interrupt_data = interrupt_obj

    # Only create the memory message if it doesn't already exist
    if not any(msg.get("message_type") == "memory" for msg in st.session_state.messages):
        add_new_message("assistant", interrupt_data['suggested_memories'], "memory")


def setup_chat_interface(column):
    """Setup and handle the chat interface."""
    # Display chat messages from history on app rerun
    for i, message in enumerate(st.session_state.messages):
        if message["role"] == "assistant" and message.get("message_type") == "draft":
            display_draft_message(message, i, column)
        elif message["role"] == "assistant" and message.get("message_type") == "memory":
            display_memory_message(message, i, column)
        else:
            display_user_message(message, column)

    # Show new job button if job is completed
    if st.session_state.job_completed:
        if st.button("Start a New Task", key="new_job_button"):
            handle_new_job()

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
    user_options = ["None Selected"] + available_users

    # Use persisted user if available, otherwise use current state user
    if st.session_state.persisted_user in user_options:
        default_index = user_options.index(st.session_state.persisted_user)
    elif st.session_state.current_state["original_request"]:
        default_index = user_options.index(st.session_state.current_state["user"])
    else:
        default_index = 0
    
    selected_user = st.sidebar.selectbox("Select User:", user_options, index=default_index)

    if selected_user == "None Selected":
        st.warning("No user selected. Memories will be generated for demonstration, but will not be saved.")

    # Update current state with selected user and trigger rerun if changed
    if selected_user != st.session_state.current_state["user"]:
        st.session_state.current_state["user"] = selected_user
        st.session_state.persisted_user = selected_user  # Persist the selection
        
        # Fetch and add user memories to state
        if selected_user != "None Selected":
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

    # Display graph
    with st.sidebar.expander("Graph Visualization"):
        graph = create_chat_graph()
        img_bytes = graph.get_graph().draw_mermaid_png()  
        st.image(img_bytes)


def setup_page_layout():
    """Setup the main page layout."""
    st.set_page_config(page_title="ContextCraft", page_icon="💡", layout="wide")

    header = st.container()
    header.title("💡 ContextCraft")
    # Display state in collapsible box above chat
    with header.expander("Current State", expanded=False):
        st.json(st.session_state.current_state)

    header.write("""<div class='fixed-header'/>""", unsafe_allow_html=True)

    ### Custom CSS for the sticky header
    st.markdown(
        """
    <style>
        div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
            position: sticky;
            top: 2.875rem;
            background-color: white;
            z-index: 999;
        }
        .fixed-header {
            border-bottom: 1px solid black;
        }
    </style>
        """,
        unsafe_allow_html=True
    )


# Initialize user manager
user_manager = UserManager()

# Check for API key
if not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️ Please set your OPENAI_API_KEY environment variable")
    st.stop()

# Initialize session state
initialize_session_state()

# Setup page layout
setup_page_layout()

# Setup chat interface
setup_chat_interface(st)

# Setup sidebar
setup_sidebar()
