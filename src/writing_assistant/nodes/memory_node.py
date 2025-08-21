from ..chat_state import ChatState
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List
from langgraph.types import Command
from langgraph.graph import END

class MemoryExtraction(BaseModel):
    """Structured output for memory extraction"""
    memories: List[str] = Field(
        description="List of new memory statements extracted from the revision cycle. Each memory should be a clear, actionable statement that can guide future writing. If no new meaningful insights emerge, this should be an empty list."
    )

PROMPT = """
You are a writing assistant that has just completed a revision cycle based on user feedback. Your task is to analyze the interaction and extract any new memories or insights that could help improve future writing for this user.

Context:
- Original Request: {original_request}
- Initial Draft: {initial_draft}
- User Feedback: {feedback}
- Revised Draft: {current_draft}
- Past Revisions: {past_revisions}

Based on this revision cycle, identify any new insights about the user's writing preferences, communication style, or specific requirements that should be remembered for future interactions. Focus on:

1. Writing style preferences (tone, formality, length, etc.)
2. Content preferences (what they want to emphasize or avoid)
3. Communication patterns (how they provide feedback, what they value)
4. Specific requirements or constraints they mentioned
5. Any recurring themes or patterns in their requests

Extract 1-3 concise memory statements that capture the most important insights. Each memory should be a clear, actionable statement that can guide future writing.

If no new meaningful insights emerge from this interaction, return an empty list of memories.
"""

def memory_extraction_node(state: ChatState) -> ChatState:
    """Extract new memories from revision cycles to improve future writing"""
    state["action_log"].append("Memory extraction node was invoked.")
    
    # Format past revisions for context
    past_revisions_text = ""
    if state["past_revisions"]:
        for i, revision in enumerate(state["past_revisions"], 1):
            past_revisions_text += f"Round {i}:\n"
            past_revisions_text += f"Feedback: {revision['feedback']}\n"
            past_revisions_text += f"Draft: {revision['draft']}\n\n"
    
    # Get the initial draft (first item in past_revisions if available)
    initial_draft = ""
    if state["past_revisions"]:
        initial_draft = state["past_revisions"][0]["draft"]
    
    prompt = PROMPT.format(
        original_request=state["original_request"],
        initial_draft=initial_draft,
        feedback=state["feedback"],
        current_draft=state["current_draft"],
        past_revisions=past_revisions_text
    )
    
    # Get response from OpenAI with structured output
    llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=300)
    llm_with_structure = llm.bind_tools([MemoryExtraction])
    memories = llm_with_structure.invoke(prompt).tool_calls[0]["args"]["memories"]

    if len(memories) > 0:
        return Command(goto="confirm_memories", update={"suggested_memories": memories})
    else:
        return Command(goto=END)