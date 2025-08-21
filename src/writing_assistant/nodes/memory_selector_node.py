from ..chat_state import ChatState
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List

class MemorySelection(BaseModel):
    """Structured output for memory selection"""
    applicable_memories: List[str] = Field(
        description="List of memory statements that are applicable to the current request. Only include memories that are directly relevant to the user's current writing task."
    )

PROMPT = """
You are a writing assistant that needs to select which user memories are applicable to the current writing request.

Current Request:
{original_request}

Available Memories:
{available_memories}

Your task is to analyze the current request and determine which memories are applicable and relevant to this specific writing task.

Consider:
1. Writing style preferences (tone, formality, length, structure)
2. Content preferences (what they want to emphasize or avoid)
3. Communication patterns (how they provide feedback, what they value)
4. Specific requirements or constraints they mentioned
5. Contextual information about their communication style

Only select memories that are directly relevant to the current request. If a memory is not applicable to this specific task, do not include it.

Return only the memory statements that are applicable, maintaining their original wording.
"""

def memory_selector_node(state: ChatState) -> ChatState:
    """Select which memories are applicable to the current request"""
    state["action_log"].append("Memory selector node was invoked.")
    
    # If no memories exist, return empty list
    if not state.get("memories") or len(state["memories"]) == 0:
        state["applicable_memories"] = []
        return state
    
    # Format available memories
    available_memories = "\n".join([f"- {memory}" for memory in state["memories"]])
    
    prompt = PROMPT.format(
        original_request=state["original_request"],
        available_memories=available_memories
    )
    
    # Get response from OpenAI with structured output
    llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=300)
    llm_with_structure = llm.bind_tools([MemorySelection])
    result = llm_with_structure.invoke(prompt)
    
    # Extract applicable memories
    applicable_memories = result.tool_calls[0]["args"]["applicable_memories"]
    
    # Update state
    state["applicable_memories"] = applicable_memories
    
    return state
