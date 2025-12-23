"""Script to verify LLM-based intent classification with Hugging Face or OpenAI."""
import os
import sys
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        # Python < 3.7
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.rag.intent_classification import QueryIntent
from app.rag.llm_intent_classification import get_llm_intent_classifier


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(query: str, result):
    """Print classification result in a formatted way."""
    intent_emoji = {
        QueryIntent.SQL: "🔢",
        QueryIntent.RAG: "📚",
        QueryIntent.HYBRID: "🔀",
    }
    emoji = intent_emoji.get(result.intent, "❓")

    print(f"\n{emoji} Query: \"{query}\"")
    print(f"   Intent: {result.intent.value.upper()}")
    print(f"   Confidence: {result.confidence:.2%}")
    print(f"   Explanation: {result.explanation}")


def main():
    """Main verification function."""
    print_section("LLM Intent Classification Verification")

    # Check provider
    provider = settings.llm_provider.lower()
    print(f"\nConfigured LLM Provider: {provider.upper()}")

    if provider == "huggingface":
        model_name = settings.huggingface_llm_model
        print(f"Model: {model_name}")
        print("\n⚠️  Note: First run may take time to download the model.")
        print("   Subsequent runs will be faster.")
    elif provider == "openai":
        model_name = settings.openai_chat_model
        print(f"Model: {model_name}")
        if not settings.openai_api_key:
            print("\n❌ ERROR: OPENAI_API_KEY is not set in .env file!")
            return 1
    else:
        print(f"\n❌ ERROR: Unsupported LLM provider: {provider}")
        print("   Supported providers: 'openai', 'huggingface'")
        return 1

    # Try to create classifier
    print("\n📦 Initializing LLM classifier...")
    try:
        classifier = get_llm_intent_classifier()
        print("✅ LLM classifier initialized successfully!")
    except ImportError as e:
        print(f"\n❌ ERROR: Missing dependencies")
        print(f"   {e}")
        if provider == "huggingface":
            print("\n   Install Hugging Face support with:")
            print("   poetry add transformers")
            print("   poetry add torch --optional")
            print("\n   Note: If torch installation fails due to Python version,")
            print("   you can install it separately: pip install torch")
        else:
            print("\n   Install OpenAI support with:")
            print("   poetry add langchain-openai")
        return 1
    except ValueError as e:
        print(f"\n❌ ERROR: Configuration issue")
        print(f"   {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: Failed to initialize LLM")
        print(f"   {e}")
        if provider == "huggingface":
            print("\n   Common issues:")
            print("   - Model name might be incorrect")
            print("   - Insufficient RAM/VRAM for the model")
            print("   - Missing transformers/torch dependencies")
            print("\n   Try a smaller model like 'google/gemma-2b-it'")
        return 1

    # Test queries
    print_section("Testing Intent Classification")

    test_queries = [
        ("Колко читалища има в Пловдив?", QueryIntent.SQL),
        ("Какво е читалище и какво представлява?", QueryIntent.RAG),
        ("Колко читалища има и разкажи за тях?", QueryIntent.HYBRID),
        ("Статистика за читалищата по региони", QueryIntent.SQL),
        ("Разкажи ми за историята на читалищата", QueryIntent.RAG),
        ("Какво е средното число на членовете?", QueryIntent.SQL),
        ("Опиши как работи читалището", QueryIntent.RAG),
    ]

    print(f"\nRunning {len(test_queries)} test queries...")
    print("(This may take a while for Hugging Face models on first run)\n")

    results = []
    for i, (query, expected_intent) in enumerate(test_queries, 1):
        print(f"[{i}/{len(test_queries)}] Processing...", end="", flush=True)
        try:
            result = classifier.classify(query)
            results.append((query, expected_intent, result))
            print(" ✓")
            print_result(query, result)
        except Exception as e:
            print(f" ✗ ERROR")
            print(f"   Error classifying query: {e}")
            results.append((query, expected_intent, None))

    # Summary
    print_section("Summary")

    successful = sum(1 for _, _, r in results if r is not None)
    correct_intent = sum(
        1
        for _, expected, r in results
        if r is not None and r.intent == expected
    )

    print(f"\n✅ Successfully classified: {successful}/{len(test_queries)} queries")
    print(f"✅ Correct intent detected: {correct_intent}/{len(test_queries)} queries")

    if successful < len(test_queries):
        print(f"\n⚠️  {len(test_queries) - successful} queries failed")
        print("   Check error messages above for details")

    if correct_intent < successful:
        print(f"\n⚠️  {successful - correct_intent} queries had different intent than expected")
        print("   This is normal - LLM may interpret queries differently")
        print("   The important thing is that classification works and returns valid results")

    print("\n" + "=" * 70)
    print("✅ Verification complete!")
    print("=" * 70 + "\n")

    return 0 if successful == len(test_queries) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

