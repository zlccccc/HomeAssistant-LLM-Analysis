#!/bin/bash
# Activation script for Home Assistant LLM Analysis environment

# Activate the virtual environment
source .venv/bin/activate

# Optional: Show the Python version being used
echo "Using Python: $(python --version)"

# Display installed packages
echo "Environment activated. Available packages include:"
echo "- gradio (UI framework)"
echo "- pandas (data manipulation)"
echo "- langchain (LLM orchestration)"
echo "- langgraph (state management)"
echo "- requests (HTTP client)"
echo "- python-dotenv (environment variables)"
echo ""
echo "You can now run the application with:"
echo "python ha_chat_assistant.py"
echo ""
echo "Or run the entity analyzer with:"
echo "python analyze_entities.py"