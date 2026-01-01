"""Verify embedding services configuration."""
import argparse
import sys
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.rag.embeddings import (
    OpenAIEmbeddingService,
    get_embedding_service,
)


def verify_current_config():
    """Quick verification of currently configured embedding provider."""
    print("Verifying Embedding Configuration")
    print("=" * 50)
    print(f"Provider: {settings.embedding_provider}")
    print()

    try:
        # Get embedding service based on config
        print("1. Loading embedding service...")
        embedding_service = get_embedding_service()
        print(f"   [OK] Service type: {type(embedding_service).__name__}")

        # Show provider-specific config
        if hasattr(embedding_service, "model_name"):
            print(f"   [OK] Model: {embedding_service.model_name}")
        elif hasattr(embedding_service, "model"):
            print(f"   [OK] Model: {embedding_service.model}")

        # Test embedding
        print("\n2. Testing embedding generation...")
        test_text = "Читалище 'Просвета' в град Пловдив е активно читалище с богата история."
        embedding = embedding_service.embed_text(test_text)
        dimension = embedding_service.get_dimension()

        print(f"   [OK] Embedding dimension: {dimension}")
        print(f"   [OK] Sample embedding (first 5 values): {embedding[:5]}")

        # Test batch
        print("\n3. Testing batch embedding...")
        test_texts = [
            "Първо читалище",
            "Второ читалище",
            "Трето читалище",
        ]
        embeddings = embedding_service.embed_texts(test_texts)
        print(f"   [OK] Batch size: {len(embeddings)}")
        print(f"   [OK] All embeddings have {len(embeddings[0])} dimensions")

        print("\n" + "=" * 50)
        print("[SUCCESS] Embedding configuration is working correctly!")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"\n[ERROR] Configuration error: {e}")
        import traceback
        traceback.print_exc()
        print("\nPlease check your .env file configuration.")
        return False


def test_openai_embeddings():
    """Test OpenAI embedding service (requires API key)."""
    print("\nTesting OpenAI embedding service...")
    print("-" * 50)

    try:
        service = OpenAIEmbeddingService()
        print(f"[OK] Model: {service.model}")

        # Test single text
        test_text = "Това е тестов текст на български език."
        embedding = service.embed_text(test_text)
        dimension = service.get_dimension()
        print(f"[OK] Single text embedding: {dimension} dimensions")

        # Test batch
        test_texts = [
            "Първи тестов текст.",
            "Втори тестов текст.",
            "Трети тестов текст.",
        ]
        embeddings = service.embed_texts(test_texts)
        print(f"[OK] Batch embeddings: {len(embeddings)} texts, {len(embeddings[0])} dimensions each")

        print("\n[SUCCESS] OpenAI embeddings work correctly!")
        return True

    except ValueError as e:
        if "API key" in str(e):
            print(f"[SKIP] OpenAI test skipped: {e}")
            print("       Set OPENAI_API_KEY in .env to test OpenAI embeddings")
            return True  # Not a failure, just missing config
        raise
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_embedding_factory():
    """Test embedding service factory."""
    print("\nTesting embedding service factory...")
    print("-" * 50)

    try:
        # Test OpenAI via factory (if API key is set)
        try:
            service_openai = get_embedding_service("openai")
            print(f"[OK] Factory returned OpenAI service: {type(service_openai).__name__}")
        except ValueError as e:
            if "API key" in str(e):
                print(f"[SKIP] OpenAI factory test skipped: {e}")
            else:
                raise

        # Test invalid provider
        try:
            get_embedding_service("invalid")
            print("[ERROR] Factory should have raised ValueError for invalid provider")
            return False
        except ValueError:
            print("[OK] Factory correctly rejects invalid provider")

        print("\n[SUCCESS] Embedding factory works correctly!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_comprehensive_tests():
    """Run comprehensive tests for all embedding providers."""
    print("=" * 50)
    print("Embedding Services Initialization & Verification")
    print("=" * 50)

    results = []

    # Test OpenAI (requires API key)
    results.append(("OpenAI", test_openai_embeddings()))

    # Test factory
    results.append(("Factory", test_embedding_factory()))

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    for name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {name}")

    all_passed = all(result[1] for result in results)
    if all_passed:
        print("\n[SUCCESS] All tests passed!")
    else:
        print("\n[WARNING] Some tests failed or were skipped")

    return all_passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Verify embedding services configuration"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run comprehensive tests for all providers (default: quick verification of current config)",
    )
    args = parser.parse_args()

    if args.all:
        success = run_comprehensive_tests()
    else:
        success = verify_current_config()

    sys.exit(0 if success else 1)
