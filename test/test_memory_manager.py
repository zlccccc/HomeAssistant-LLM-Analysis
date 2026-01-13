"""
Memory Manager Test Script

This script tests the MemU memory management functionality.
Run with: uv run python test/test_memory_manager.py
"""
import asyncio
import os
import sys

# Add backend to Python path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import after path is set
from dotenv import load_dotenv

load_dotenv()

from backend.source.api_layer.memory_manager import memory_manager


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def print_result(label: str, success: bool, detail: str = ""):
    """Print a test result."""
    symbol = "[OK]" if success else "[FAIL]"
    print(f"  {symbol} {label}")
    if detail:
        print(f"      -> {detail}")


async def test_initialization():
    """Test memory manager initialization."""
    print_section("1. Memory Manager Initialization")

    # Check if memory manager exists
    has_manager = hasattr(memory_manager, 'memory')
    print_result("Memory manager object exists", has_manager)

    if has_manager:
        is_enabled = memory_manager.memory is not None
        if is_enabled:
            print_result("Memory service is enabled", True,
                        f"Type: {type(memory_manager.memory).__name__}")
        else:
            print_result("Memory service is disabled", False,
                        "USE_MEMORY_MESSAGES is not 'true' or no API key found")
    return has_manager


async def test_environment():
    """Test environment configuration."""
    print_section("2. Environment Configuration")

    use_memory = os.environ.get("USE_MEMORY_MESSAGES", "false")
    print_result("USE_MEMORY_MESSAGES", use_memory == "true", use_memory)

    qwen_key = os.environ.get("QWEN_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if qwen_key:
        print_result("QWEN_API_KEY configured", True, f"sk-{qwen_key[:8]}...")
    else:
        print_result("QWEN_API_KEY configured", False, "Not set")

    if openai_key:
        print_result("OPENAI_API_KEY configured", True, f"sk-{openai_key[:8]}...")
    else:
        print_result("OPENAI_API_KEY configured", False, "Not set")

    user_id = os.environ.get("MEMU_USER_ID", "user001")
    print_result("MEMU_USER_ID", True, user_id)


async def test_memorize():
    """Test memorize functionality."""
    print_section("3. Test Memorize Function")

    if memory_manager.memory is None:
        print_result("Memorize test", False, "Memory is not enabled")
        return

    # Test with sample messages
    test_messages = [
        {"role": "user", "content": "你好，我喜欢温度设定在 24 度"},
        {"role": "assistant", "content": "好的，我记住了您偏好 24 度的室温。"},
        {"role": "user", "content": "请把客厅的灯打开"},
    ]

    try:
        result = await memory_manager.memorize_messages(test_messages)
        status = result.get("status", "unknown")

        if status == "success":
            count = result.get("memorized_count", 0)
            print_result("Memorize messages", True, f"Memorized {count} messages")
        elif status == "disabled":
            print_result("Memorize messages", False, "Memory is disabled")
        elif status == "error":
            error = result.get("error", "Unknown error")
            print_result("Memorize messages", False, f"Error: {error}")
        else:
            print_result("Memorize messages", False, f"Unknown status: {status}")

    except Exception as e:
        print_result("Memorize messages", False, f"Exception: {e}")


async def test_retrieve():
    """Test retrieve functionality."""
    print_section("4. Test Retrieve Function")

    if memory_manager.memory is None:
        print_result("Retrieve test", False, "Memory is not enabled")
        return

    try:
        result = await memory_manager.retrieve_memory_info("用户偏好设置")

        if result:
            lines = result.strip().split('\n')
            print_result("Retrieve memory", True,
                        f"Retrieved {len(lines)} lines of content")
            print("\n  --- Retrieved Content Preview ---")
            preview = '\n  '.join(result.split('\n')[:10])
            print(f"  {preview}")
            if len(result.split('\n')) > 10:
                print("  ... (truncated)")
            print("  --- End Preview ---\n")
        else:
            print_result("Retrieve memory", False,
                        "No memory retrieved (may be empty or error)")

    except Exception as e:
        print_result("Retrieve memory", False, f"Exception: {e}")


async def test_edge_cases():
    """Test edge cases."""
    print_section("5. Edge Cases")

    if memory_manager.memory is None:
        print_result("Edge case tests", False, "Memory is not enabled")
        return

    # Test empty list
    try:
        result = await memory_manager.memorize_messages([])
        status = result.get("status", "")
        print_result("Empty message list", status == "no_messages", f"Status: {status}")
    except Exception as e:
        print_result("Empty message list", False, f"Exception: {e}")

    # Test None input (should handle gracefully or raise clear error)
    try:
        result = await memory_manager.memorize_messages(None)
        if isinstance(result, dict):
            status = result.get("status", "")
            print_result("None input handling", True, f"Status: {status}")
        else:
            print_result("None input handling", False, f"Unexpected return: {type(result)}")
    except (TypeError, AttributeError) as e:
        print_result("None input handling", True, f"Raises expected error: {type(e).__name__}")
    except Exception as e:
        print_result("None input handling", False, f"Unexpected exception: {e}")


async def main():
    """Main test runner."""
    print_section("Memory Manager Test Suite")
    print("\nTesting MemU memory management functionality.")
    print("Note: Some tests may fail if memory is not properly configured.\n")

    try:
        # Run all tests
        await test_initialization()
        await test_environment()
        await test_memorize()
        await test_retrieve()
        await test_edge_cases()

        print_section("Test Summary")
        print("\n  All tests completed.")
        print("\n  Configuration Guide:")
        print("  - Enable memory: Set USE_MEMORY_MESSAGES=true")
        print("  - For Qwen: Set QWEN_API_KEY")
        print("  - For OpenAI: Set OPENAI_API_KEY")
        print("  - Optional: Set MEMU_USER_ID (default: user001)")

    except KeyboardInterrupt:
        print("\n\n[Test interrupted by user]")
    except Exception as e:
        print(f"\n\n[Fatal error: {e}]")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
