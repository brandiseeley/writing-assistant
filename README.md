# ContextCraft: AI Writer with Memory

An AI writing assistant that learns your communication style through feedback. Built with LangGraph, it automatically captures and applies your writing preferences to create increasingly personalized drafts without repeated prompt engineering.

## Setup

1. **Install dependencies & activate venv**:
   ```bash
   poetry install
   eval $(poetry env activate)
   ```

2. **Create `.env` file** in the project root with your API keys:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here

   # Optional for Tracing
   LANGSMITH_API_KEY=your_langsmith_api_key_here
   LANGSMITH_TRACING=true
   ```

3. **Run the app**:
   ```bash
   streamlit run streamlit_app.py
   ```

## How It Works

1. Request writing assistance
2. Review the generated draft
3. Provide feedback or approve
4. The system learns from your feedback and applies it to future drafts

The more you use it, the better it understands your style and preferences.
