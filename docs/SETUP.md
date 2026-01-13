# Home Assistant LLM Analysis - Setup with uv

This project uses `uv` for fast dependency management and virtual environment creation.

## Setup

1. **Install uv** (if not already installed):
   ```bash
   pip install uv
   # or
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Create virtual environment**:
   ```bash
   uv venv
   ```

   Note: uv automatically selects the best available Python version. If Python 3.13+ is available on your system, uv will use it. In this case, Python 3.14.0 was selected.

3. **Install dependencies**:
   Dependencies have already been installed in the virtual environment using:
   ```bash
   # Install individual packages (what was done)
   source .venv/bin/activate && uv pip install requests openpyxl pandas gradio pydantic python-dotenv 'httpx[socks]' langchain langchain-core langchain-openai langgraph langchain-mcp-adapters memu-py loguru
   ```

4. **Activate the environment**:
   ```bash
   source .venv/bin/activate
   # or run the provided script:
   ./activate_env.sh
   ```

## Project Structure

The project has been converted to use modern Python packaging with the following key files:
- `pyproject.toml` - Project metadata and dependencies
- `.venv/` - Virtual environment directory
- `activate_env.sh` - Helper script to activate the environment

## Running the Application

After activating the virtual environment, you can run:

- Main application: `python ha_chat_assistant.py`
- Entity analyzer: `python analyze_entities.py`

## Audio Dependencies

The optional audio dependencies (pyaudio, pygame, playsound, pydub) require system-level dependencies that need to be installed separately:

```bash
# On Ubuntu/Debian:
sudo apt-get install portaudio19-dev python3-pyaudio

# Then install the Python packages:
uv pip install pyaudio pygame pydub
```

Note: `playsound` may not work on Linux systems. Use `pygame` or `pydub` for audio playback.

## Compatibility Note

With Python 3.14+, you may see warnings about Pydantic V1 compatibility. These are warnings only and shouldn't prevent the application from functioning. The core functionality of LangChain and related packages remains intact.