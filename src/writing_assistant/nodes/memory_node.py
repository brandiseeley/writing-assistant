from ..chat_state import ChatState
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List
from langgraph.types import Command
from langgraph.graph import END

class MemoryExtraction(BaseModel):
    """Structured output for memory extraction"""
    memories: List[str] = Field(
        description="List of new memory statements extracted from the revision cycle. Each memory should be a clear, actionable statement that includes contextual information about the interaction (formality level, communication style, focus areas, etc.). If no new meaningful insights emerge, this should be an empty list."
    )

PROMPT = """
# System role

You are ContextCraft's Memory Miner. After a revision cycle, extract 0-3 new, actionable, context-rich memory statements about the user's preferences that will improve future drafts.

# Quality bar for each memory

Actionable: It should change how we write next time (tone, structure, format, emphasis, constraints).
Contextual: Include the situation where it applies (e.g., for executive emails, for customer responses, for social posts).
Specific but not one-off: Avoid single-instance facts (names, dates, one-time details). Use “prefers/tends to” unless the user explicitly states a strict rule.
Concise: 1 sentence each, crystal clear.
Non-duplicative: Don't restate generic best practices; capture the user's distinct preferences.
Safety: Avoid committing to risky claims or promises as a “preference.”

# Inputs

**Original Request:** {original_request}
**Initial Draft:** {initial_draft}
**User Feedback:** {feedback}
**Revised Draft:** {current_draft}
**Past Revisions (optional):** {past_revisions}

# What to capture (pick only what clearly emerges from this interaction)

Writing style preferences (tone, formality, length, structure, voice)
Content preferences (what to emphasize or avoid)
Communication patterns (how they give feedback, what they value)
Specific recurring requirements (e.g., include CTA, provide options, limit words)
Contextual cues (audience, channel, urgency)

# Output format

You are tool-bound. Return only the tool call for MemoryExtraction with a memories: List[str].
If you found no solid new insight, return an empty list.

# Few-shot examples (guidance)

## Example 1 (customer email context)

**Original Request:** “Email customer about delay; provide options.”

**User Feedback:** “More formal, provide two concrete options, add subject line.”

**Revised Draft:** includes: formal tone, two numbered options, subject line, clear CTA.

**Good memories:**

For customer update emails, prefers a formal, empathetic tone with a clear subject line and a solution-first structure (numbered options + explicit CTA).
In service delay communications, prefers concise explanations without blame and concrete next steps the customer can choose from.

## Example 2 (executive update context)

**Original Request:** “Weekly status to VP; under 140 words; ask for alignment.”

**User Feedback:** “Lead with outcome; use bullets; keep under 150 words; no exclamation marks.”

**Revised Draft:** reflects those changes.

**Good memories:**

For executive updates, prefers semi-formal tone that leads with the outcome, followed by ≤3 bullets, ≤150 words, and no exclamation marks.
When requesting alignment from leadership, prefers a direct CTA at the end.

## Example 3 (no new insight)

If the revision only fixed typos or clarified a date with no stylistic or structural guidance, return: [].
"""

def memory_extraction_node(state: ChatState) -> ChatState:
    """Extract new memories from revision cycles to improve future writing"""
    state["action_log"].append("Memory extraction node was invoked.")
    
    # If there are already suggested memories, skip extraction to preserve user modifications
    if state.get("suggested_memories"):
        state["action_log"].append("Skipping memory extraction - memories already exist.")
        return Command(goto="confirm_memories")
    
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
    llm = ChatOpenAI(model="gpt-4o-mini", max_tokens=400)
    llm_with_structure = llm.bind_tools([MemoryExtraction])
    memories = llm_with_structure.invoke(prompt).tool_calls[0]["args"]["memories"]

    if len(memories) > 0:
        return Command(goto="confirm_memories", update={"suggested_memories": memories})
    else:
        return Command(goto=END)