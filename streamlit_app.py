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

# Initialize user manager
user_manager = UserManager()

# Page config
st.set_page_config(page_title="Writing Assistant", page_icon="📝", layout="wide")
st.title("📝 Writing Assistant")
left_column, right_column = st.columns(2)

# Check for API key
if not os.getenv("OPENAI_API_KEY"):
    st.error("⚠️ Please set your OPENAI_API_KEY environment variable")
    st.stop()

# Initialize session state
if "chat_graph" not in st.session_state:
    st.session_state.chat_graph = create_chat_graph()
if "config" not in st.session_state:
    st.session_state.config = {"configurable": {"thread_id": uuid.uuid4()}}
if "current_state" not in st.session_state:
    st.session_state.current_state = initialize_chat_state()
    st.session_state.current_state["action_log"] = [f'Graph was initialized. ConfigID: {str(st.session_state.config["configurable"]["thread_id"])[:6]}...']

# Simple controls - LEFT COLUMN
left_column.header("Controls")
new_message = left_column.text_input("Send Request:")
if left_column.button("Send"):
    if new_message.strip():
        st.session_state.current_state["action_log"].append("User sent a request.")
        st.session_state.current_state["original_request"] = new_message
        try:
            result = st.session_state.chat_graph.invoke(st.session_state.current_state, config=st.session_state.config)
            st.session_state.current_state = result
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

if left_column.button("Reset"):
    st.session_state.current_state = initialize_chat_state()
    st.rerun()

# Generic interrupt handling section
# This handles any type of interrupt from the graph nodes
# Each interrupt should have a "type" field and optionally a "message" field
if st.session_state.current_state.get("__interrupt__"):
    # Handle the interrupt object structure
    interrupt_obj = st.session_state.current_state["__interrupt__"][0]
    
    if hasattr(interrupt_obj, 'value'):
        interrupt_data = interrupt_obj.value
    else:
        interrupt_data = interrupt_obj

    if interrupt_data["type"] == "draft":
        with left_column.form("draft_feedback_form"):
            feedback = st.text_area("Feedback (optional):", placeholder="Enter feedback if you want to revise...")
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.form_submit_button("Approve"):
                    st.session_state.current_state["action_log"].append(f"User approved draft. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
                    result = st.session_state.chat_graph.invoke(Command(resume={"action": "approve", "feedback": ""}), config=st.session_state.config)
                    st.session_state.current_state = result
                    st.rerun()
            with col2:
                if st.form_submit_button("Reject"):
                    st.session_state.current_state["action_log"].append(f"User rejected draft. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
                    result = st.session_state.chat_graph.invoke(Command(resume={"action": "reject", "feedback": "none"}), config=st.session_state.config)
                    st.session_state.current_state = result
                    st.rerun()
            with col3:
                if st.form_submit_button("Revise"):
                    if feedback.strip():
                        st.session_state.current_state["action_log"].append(f"User requested revision. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
                        result = st.session_state.chat_graph.invoke(Command(resume={"action": "revise", "feedback": feedback}), config=st.session_state.config)
                        st.session_state.current_state = result
                        st.rerun()
                    else:
                        st.error("Please provide feedback for revision.")
    
    elif interrupt_data["type"] == "memory_confirmation":
        for i, suggested_memory in enumerate(interrupt_data["suggested_memories"]):
            left_column.write(f"{i+1}. {suggested_memory}")
            if left_column.button(f"Save Memory {i+1}", key=f"save_memory_{i}"):
                st.session_state.current_state["action_log"].append(f"User confirmed memory #{i+1}")
                st.session_state.current_state["new_memories"].append(suggested_memory)
                st.rerun()
        if left_column.button("Confirm"):
            st.session_state.current_state["action_log"].append(f"User confirmed memories. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
            result = st.session_state.chat_graph.invoke(Command(resume={"action": "confirm_memories", "new_memories": st.session_state.current_state["new_memories"]}), config=st.session_state.config)
            st.session_state.current_state = result
            st.rerun()

# Display state - RIGHT COLUMN
right_column.header("Current State")
right_column.json(st.session_state.current_state)

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
