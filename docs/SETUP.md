# Setup

## Quick Start

1. **Install uv** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies**:
   ```bash
   uv sync --extra dev
   ```

   For voice playback support, also install the speech extra:
   ```bash
   uv sync --extra dev --extra speech
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and fill in your API keys and configuration
   ```

4. **Run the application**:
   ```bash
   uv run python frontend/ha_chat_assistant.py
   # or
   ./scripts/dev.sh run
   ```

## Environment Variables

Edit `.env` with your values:

| Variable | Description |
|----------|-------------|
| `HA_URL` | Home Assistant URL |
| `HA_TOKEN` | Home Assistant long-lived access token |
| `QWEN_API_KEY` | Qwen API key |
| `QWEN_API_BASE` | Qwen API base URL |
| `QWEN_MODEL` | LLM model name |
| `QWEN_ASR_MODEL` | Speech recognition model |
| `QWEN_TTS_MODEL` | Text-to-speech model |
| `OUTPUT_DIR` | Output directory path |
| `HA_MCP_ENDPOINT` | MCP service endpoint |
| `USE_MEMORY_MESSAGES` | Enable memory feature (`true`/`false`) |
| `MEMU_API_KEY` | MemU API key |
| `MEMU_USER_ID` | MemU user ID |
| `MEMU_USER_NAME` | MemU user name |
| `MEMU_AGENT_ID` | MemU agent ID |

## Audio Dependencies

Voice features require system-level packages:

```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev python3-pyaudio
```

Note: `playsound` may not work on Linux. The project uses `pygame` or `pydub` for audio playback.

## Entity Analyzer

```bash
uv run python frontend/tools/analyze_entities.py
```
