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

# Other
run          Run the application
analyze      Run entity analysis tool
```

## Architecture

```
frontend/ha_chat_assistant.py          # Gradio UI entry point
backend/source/
├── home_assistant_llm_controller_langgraph.py  # LangGraph controller
├── command_parser.py                  # Command parsing
└── api_layer/
    ├── home_assistant.py              # HA API client
    ├── llm_manager.py                 # LLM client
    ├── memory_manager.py              # MemU memory client
    └── qwen_speech_model.py           # Speech (ASR/TTS)
```

## Test Markers

- `unit`: No external deps
- `integration`: May require external services
- `slow`: Skip with `-m "not slow"`
- `requires_ha`: Needs Home Assistant
- `requires_llm`: Needs LLM API

## Documentation

- `docs/README.md` - Project overview
- `docs/SETUP.md` - Setup guide
- `docs/README_MEMU.md` - MemU memory system
- `openspec/AGENTS.md` - OpenSpec specification

---

## Coding Conventions

### Error Logging

**Always use `logger.error()` for exceptions**:

```python
# ✅ Correct
try:
    result = await some_async_function()
except Exception as e:
    logger.error(f"操作失败: {e!s}")
    import traceback
    logger.error(f"详细错误: {traceback.format_exc()}")
```

### Async Functions

**Functions calling async operations must be `async` and use `await`**:

```python
# ✅ Correct
async def _memory_messages(self, state: State):
    result = await memory_manager.memorize_messages(messages)

# ❌ Wrong - causes "no running event loop" errors
def _memory_messages(self, state: State):
    loop = asyncio.new_event_loop()  # Don't create new loops!
```

### Timeout Handling

**Use `asyncio.wait_for` for operations that may hang**:

```python
result = await asyncio.wait_for(
    some_async_operation(),
    timeout=15.0
)
except asyncio.TimeoutError:
    logger.warning("操作超时，跳过")
```

**Timeouts**:
- `memorize_messages`: 15 seconds
- `retrieve_memory_info`: 10 seconds

### Function Calls

**Always use named parameters (keyword arguments)**:

```python
# ✅ Correct
response = await hass_llm_controller.process_home_assistant_message(
    message="hello",
    history=history
)

# ❌ Wrong - unclear
response = await hass_llm_controller.process_home_assistant_message("hello", history)
```

### Function Documentation

**Always include usage examples in docstrings**:

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

**Docstring format**:
- `Args:` section documenting parameters
- `Returns:` section documenting return value
- `Example:` section with `>>>` prompt style
- Show `await` for async functions

## Testing Guidelines

### Test Isolation

**Unit tests should not auto-load `.env` or connect to external services**:

- Use `patch.dict(os.environ, {...})` for environment variables
- Mock external API calls
- Use `@pytest.mark.requires_ha` or `@pytest.mark.requires_llm` for integration tests

**Before committing, run**: `./scripts/dev.sh test-fast && ./scripts/dev.sh format && ./scripts/dev.sh lint`

**更新结束后git commit前先做询问**

**用uv环境，不要直接python**