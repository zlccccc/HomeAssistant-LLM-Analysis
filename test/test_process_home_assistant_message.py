"""
Process Home Assistant Message Test Script

Tests the message processing functionality.
Run with: uv run python test/test_process_home_assistant_message.py
"""
import asyncio
import os
import sys

# Add backend to Python path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv

load_dotenv()

from backend.source.home_assistant_llm_controller_langgraph import hass_llm_controller_langgraph


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


async def test_message_processing():
    """Test basic message processing."""
    print_section("1. Basic Message Processing")

    try:
        result = await hass_llm_controller_langgraph.process_home_assistant_message(
            "Hello, this is a test message",
            [("Previous message", "Previous response")]
        )
        print_result("Message processing", True,
                    f"Response: {result[:50]}...")
    except Exception as e:
        print_result("Message processing", False, str(e))


async def test_empty_history():
    """Test message processing with empty history."""
    print_section("2. Empty History")

    try:
        result = await hass_llm_controller_langgraph.process_home_assistant_message(
            "Test message with empty history",
            []
        )
        print_result("Empty history handled", True,
                    f"Response: {result[:50]}...")
    except Exception as e:
        print_result("Empty history handled", False, str(e))


async def test_none_history():
    """Test message processing with None history."""
    print_section("3. None History")

    try:
        result = await hass_llm_controller_langgraph.process_home_assistant_message(
            "Test message with no history",
            None
        )
        print_result("None history handled", True,
                    f"Response: {result[:50]}...")
    except Exception as e:
        print_result("None history handled", False, str(e))


async def main():
    """Main test runner."""
    print_section("Message Processing Test Suite")
    print("\nTesting Home Assistant message processing.")
    print("Note: Tests may fail if API keys are not configured.\n")

    try:
        await test_message_processing()
        await test_empty_history()
        await test_none_history()

        print_section("Test Summary")
        print("\n  All tests completed.")
        print("\n  Configuration Guide:")
        print("  - Set QWEN_API_KEY with a valid API key")

    except Exception as e:
        print(f"\n\n[Fatal error: {e}]")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n[Test interrupted by user]")
    except RuntimeError as e:
        if "Timeout should be used inside a task" in str(e):
            # Ignore nest_asyncio compatibility warning
            print("\n[Test completed]")
        else:
            raise
