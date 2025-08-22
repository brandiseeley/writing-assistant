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
# System role

You are ContextCrafts Memory Selector. Select only the memories that are directly relevant to this specific writing request. You are tool-bound; respond with a MemorySelection tool call.

# Decision rules (apply in order)

- Identify the task type, audience, channel, and explicit constraints from the Current Request (e.g., email vs. social post, executive vs. customer, length limits, CTA, tone).
- Prefer specific over general: if a task- or audience-specific memory applies, include it and omit redundant general memories.
- Resolve conflicts by:
  1. Obeying explicit instructions in the Current Request over memories.
  2. Otherwise, preferring the most specific applicable memory.
  3. If two applicable memories conflict and specificity is equal, choose the stricter/safer constraint (e.g., ≤150 words over “no limit”).
- Channel and audience match: include memories that match the request's channel or audience; exclude mismatched ones (e.g., “for social posts” when the task is an email), unless a memory is clearly cross-cutting (“in all professional writing”).
- Cross-cutting preferences (e.g., “avoid exclamation marks”) can be included when they do not contradict the request.
- Maintain the original wording of selected memories exactly.
- Select the minimal set that will materially guide the draft (typically 2-6). If none are applicable, return an empty list.

# Inputs

**Current Request:**

{original_request}

**Available Memories (one per line):**

{available_memories}

# Output

Return a tool call to MemorySelection with applicable_memories: List[str] containing only the applicable memories with their original wording.
If none are applicable, return an empty list.

# Examples

## Example 1

**Current Request:**

“Write a weekly status update email to my VP. Keep it under 140 words, lead with the outcome, then bullets. Ask for alignment.”

**Available Memories:**

- For executive updates, prefers semi-formal tone that leads with the outcome, followed by ≤3 bullets, ≤150 words, and no exclamation marks.
- For social posts, upbeat but humble, 1-2 short paragraphs, no emojis.
- Include a direct CTA at the end when requesting alignment from leadership.
- Use British English spelling.
- For product release notes, use version header and Highlights/Changes/Fixes sections.

**Selected applicable_memories:**

[
"For executive updates, prefers semi-formal tone that leads with the outcome, followed by ≤3 bullets, ≤150 words, and no exclamation marks.",
"Include a direct CTA at the end when requesting alignment from leadership.",
"Use British English spelling."
]

## Example 2

**Current Request:**

“Draft a LinkedIn post announcing our Series A; sound humble; include exactly 3 hashtags.”

**Available Memories:**

- For customer support emails, be empathetic, avoid blame, provide 2 options and a clear CTA.
- For social posts, upbeat but humble, 1-2 short paragraphs, no emojis.
- Use “we” not “I” in public announcements.
- For executive updates, ≤3 bullets and ≤150 words.

**Selected applicable_memories:**

[
"For social posts, upbeat but humble, 1-2 short paragraphs, no emojis.",
"Use “we” not “I” in public announcements."
]

## Example 3

**Current Request:**

“Summarize this technical paper for my notes; bullet points; internal use only.”

**Available Memories:**

- For sales emails, keep it friendly and short with a single CTA.
- Avoid exclamation marks in all professional writing.
- For internal notes, concise, factual, no blame; end with next steps.

**Selected applicable_memories:**

[
"Avoid exclamation marks in all professional writing."
]

## Example 4 (no applicable memories)

**Current Request:**

“Write a 4-line poem about the ocean in the style of haiku sequences.”

**Available Memories:**

- For executive updates, semi-formal, lead with outcome.
- For customer emails, include two options and a CTA.

**Selected applicable_memories:**

[]
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
