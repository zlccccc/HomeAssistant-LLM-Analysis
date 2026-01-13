"""
LLM Connection Test Script

Tests LLM functionality without requiring Home Assistant access.
Run with: uv run python test/test_llm_connection.py
"""
import asyncio
import os
import sys

# Add backend to Python path to import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv

load_dotenv()

from backend.source.api_layer.llm_manager import llm_manager


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


async def test_llm_manager():
    """Test LLM Manager initialization."""
    print_section("1. LLM Manager Initialization")

    if llm_manager.get_chat_model():
        print_result("LLM Manager has chat model", True,
                    type(llm_manager.get_chat_model()).__name__)
    else:
        print_result("LLM Manager has chat model", False,
                    "Missing API key or initialization failed")


async def test_api_call():
    """Test simple API call."""
    print_section("2. Simple API Call")

    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        response = llm_manager.call_openai_api(messages)
        print_result("API call succeeded", True,
                    f"Response: {response[:50]}...")
    except Exception as e:
        print_result("API call failed", False, str(e))


async def main():
    """Main test runner."""
    print_section("LLM Connection Test Suite")
    print("\nTesting LLM functionality without Home Assistant.")
    print("Note: Tests may fail if API keys are not configured.\n")

    try:
        await test_llm_manager()
        await test_api_call()

        print_section("Test Summary")
        print("\n  All tests completed.")
        print("\n  Configuration Guide:")
        print("  - Set QWEN_API_KEY with a valid API key")
        print("  - Set QWEN_API_BASE with the API endpoint")

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
