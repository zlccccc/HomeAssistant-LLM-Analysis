<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

## Quick Start

```bash
uv sync --extra dev                     # Install deps
cp .env.example .env                    # Configure env
uv run python frontend/ha_chat_assistant.py  # Run app
```

## Development Commands

```bash
./scripts/dev.sh <command>

# Tests
test         Run all tests
test-fast    Skip slow tests
test-cov     Run with coverage
test-html    Generate HTML coverage at :9090

# Code Quality
format       Format code (ruff)
lint         Run linter
type-check   Run type checker (mypy)
```

## Project Structure

```
frontend/ha_chat_assistant.py          # Gradio UI entry point
frontend/tools/analyze_entities.py     # Entity analysis tool

backend/source/
├── api_layer/
│   ├── home_assistant.py              # HA API client
│   ├── llm_manager.py                 # LLM client
│   └── memory_manager.py              # MemU memory client
├── services/
│   ├── command_parser.py              # Command parsing
│   ├── entity_analyzer.py             # Entity analysis
│   └── langgraph_controller.py        # LangGraph controller
├── infrastructure/
│   └── utils.py                       # Shared utilities
└── ui_service/
    ├── chat_service.py                # Chat business logic
    └── entity_service.py              # Entity business logic

frontend/api_layer/
└── qwen_speech_model.py               # Speech (ASR/TTS)
```

## Testing

```
test/
├── unit/              # Unit tests (no external deps)
├── integration/       # Integration tests (requires external services)
├── scripts/           # Manual test scripts
└── conftest.py        # Shared pytest fixtures
```

**Test markers**: `unit`, `integration`, `slow`, `requires_ha`, `requires_llm`

**Before committing**: `./scripts/dev.sh test-fast && ./scripts/dev.sh format && ./scripts/dev.sh lint`

---

## Coding Conventions

### Error Logging

Always use `logger.error()` for exceptions:

```python
try:
    result = await some_async_function()
except Exception as e:
    logger.error(f"操作失败: {e!s}")
    logger.debug(f"详细错误: {traceback.format_exc()}")
```

### Function Calls

Always use named parameters (keyword arguments):

```python
# ✅ Correct
response = await controller.process_home_assistant_message(
    message="hello",
    history=history
)

# ❌ Wrong - unclear
response = await controller.process_home_assistant_message("hello", history)
```

### Function Documentation

Include usage examples in docstrings:

```python
async def process_home_assistant_message(
    self,
    message: str,
    history: list[tuple[str, str]] = None
) -> str:
    """
    处理Home Assistant相关消息

    Args:
        message: 用户消息
        history: 历史对话，格式为 [(user_msg, assistant_msg), ...]

    Returns:
        响应消息

    Example:
        >>> controller = HomeAssistantLLMControllerLangGraph()
        >>> response = await controller.process_home_assistant_message(
        ...     message="打开客厅灯",
        ...     history=[("你好", "你好！")]
        ... )
        >>> print(response)
        "好的，我来帮您打开客厅灯。"
    """
```

### Test Isolation

Unit tests should not auto-load `.env` or connect to external services:

- Use `patch.dict(os.environ, {...})` for environment variables
- Mock external API calls
- Use `@pytest.mark.requires_ha` or `@pytest.mark.requires_llm` for integration tests

## Important Notes

- Always use `uv run python` / `uv run pip` instead of direct `python` / `pip`
- Ask before git commit
- Keep changes minimal and focused
