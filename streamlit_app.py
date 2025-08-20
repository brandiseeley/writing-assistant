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

# Page config
st.set_page_config(page_title="State Visualizer", page_icon="📝")

# Initialize user manager
user_manager = UserManager()

# Title
st.title("📝 State Visualizer")

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


# Simple controls
st.header("Controls")
new_message = st.text_input("Send Request:")
if st.button("Send"):
    if new_message.strip():
        st.session_state.current_state["action_log"].append("User sent a request.")
        st.session_state.current_state["original_request"] = new_message
        try:
            result = st.session_state.chat_graph.invoke(st.session_state.current_state, config=st.session_state.config)
            st.session_state.current_state = result
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

if st.button("approve"):
    st.session_state.chat_graph.invoke(Command(resume={"action": "approve", "feedback":"none"}), config=st.session_state.config)
    st.session_state.current_state["action_log"].append(f"User approved a draft. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")

with st.form("revise_form"):
    feedback = st.text_area("Enter your feedback:")
    if st.form_submit_button("Revise"):
        st.session_state.current_state["action_log"].append(f"User provided feedback. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
        result = st.session_state.chat_graph.invoke(Command(resume={"action": "revise", "feedback": feedback}), config=st.session_state.config)
        st.session_state.current_state = result
        st.rerun()

if st.button("reject"):
    st.session_state.current_state["action_log"].append(f"User rejected a draft. Resuming graph with ID: {str(st.session_state.config['configurable']['thread_id'])[:6]}...")
    st.session_state.chat_graph.invoke(Command(resume={"action": "reject", "feedback": "none"}), config=st.session_state.config)
    st.rerun()

if st.button("Reset"):
    st.session_state.current_state = initialize_chat_state()
    st.rerun()

# Display state
st.header("Current State")
st.json(st.session_state.current_state)

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

# Display action log
st.sidebar.header("Action Log")
for action in st.session_state.current_state["action_log"]:
    st.sidebar.write(action)

# Display graph
graph = create_chat_graph()
img_bytes = graph.get_graph().draw_mermaid_png()  
st.sidebar.image(img_bytes)
