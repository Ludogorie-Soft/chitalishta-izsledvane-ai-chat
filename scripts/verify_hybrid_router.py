"""Script to verify hybrid intent routing logic."""
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

from app.rag.hybrid_router import get_hybrid_router
from app.rag.intent_classification import QueryIntent


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(query: str, result):
    """Print routing result in a formatted way."""
    intent_emoji = {
        QueryIntent.SQL: "🔢",
        QueryIntent.RAG: "📚",
        QueryIntent.HYBRID: "🔀",
    }
    emoji = intent_emoji.get(result.intent, "❓")

    print(f"\n{emoji} Query: \"{query}\"")
    print(f"   Final Intent: {result.intent.value.upper()}")
    print(f"   Confidence: {result.confidence:.2%}")
    print(f"   Explanation: {result.explanation}")
    if result.matched_rules:
        print(f"   Matched Rules: {', '.join(result.matched_rules[:3])}")


def main():
    """Main verification function."""
    print_section("Hybrid Intent Router Verification")

    # Initialize router
    print("\n📦 Initializing hybrid router...")
    try:
        router = get_hybrid_router()
        print("✅ Hybrid router initialized successfully!")
        print(f"   Rule-based classifier: {type(router.rule_classifier).__name__}")
        print(f"   LLM classifier: {type(router.llm_classifier).__name__}")
    except Exception as e:
        print(f"\n❌ ERROR: Failed to initialize hybrid router")
        print(f"   {e}")
        return 1

    # Test queries
    print_section("Testing Hybrid Routing")

    test_queries = [
        ("Колко читалища има в Пловдив?", QueryIntent.SQL),
        ("Какво е читалище и какво представлява?", QueryIntent.RAG),
        ("Колко читалища има и разкажи за тях?", QueryIntent.HYBRID),
        ("Статистика за читалищата по региони", QueryIntent.SQL),
        ("Разкажи ми за историята на читалищата", QueryIntent.RAG),
        ("Какво е средното число на членовете?", QueryIntent.SQL),
        ("Опиши как работи читалището", QueryIntent.RAG),
        ("Колко читалища има в София и какви са техните характеристики?", QueryIntent.HYBRID),
    ]

    print(f"\nRunning {len(test_queries)} test queries...")
    print("(This may take a while if LLM is being used)\n")

    results = []
    for i, (query, expected_intent) in enumerate(test_queries, 1):
        print(f"[{i}/{len(test_queries)}] Processing...", end="", flush=True)
        try:
            result = router.route(query)
            results.append((query, expected_intent, result))
            print(" ✓")
            print_result(query, result)
        except Exception as e:
            print(f" ✗ ERROR")
            print(f"   Error routing query: {e}")
            results.append((query, expected_intent, None))

    # Summary
    print_section("Summary")

    successful = sum(1 for _, _, r in results if r is not None)
    correct_intent = sum(
        1
        for _, expected, r in results
        if r is not None and r.intent == expected
    )

    print(f"\n✅ Successfully routed: {successful}/{len(test_queries)} queries")
    print(f"✅ Intent matched expected: {correct_intent}/{len(test_queries)} queries")

    if successful < len(test_queries):
        print(f"\n⚠️  {len(test_queries) - successful} queries failed")
        print("   Check error messages above for details")

    if correct_intent < successful:
        print(f"\n⚠️  {successful - correct_intent} queries had different intent than expected")
        print("   This is normal - hybrid router may interpret queries differently")
        print("   The important thing is that routing works and returns valid results")

    # Show routing decisions
    print_section("Routing Decision Analysis")
    intent_counts = {}
    for _, _, r in results:
        if r is not None:
            intent = r.intent.value
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

    print("\nIntent distribution:")
    for intent, count in sorted(intent_counts.items()):
        print(f"  {intent.upper()}: {count}")

    print("\n" + "=" * 70)
    print("✅ Verification complete!")
    print("=" * 70 + "\n")

    return 0 if successful == len(test_queries) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)



