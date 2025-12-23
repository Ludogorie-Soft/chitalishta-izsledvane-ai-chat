"""Initialize and verify Chroma vector store setup."""
import sys
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.rag.vector_store import ChromaVectorStore


def init_chroma_db():
    """Initialize and verify Chroma vector store setup."""
    print("Initializing Chroma vector store...")
    print("-" * 50)

    try:
        # Initialize vector store
        print("1. Initializing vector store...")
        vector_store = ChromaVectorStore()
        print(f"   [OK] Persist directory: {vector_store.persist_path}")
        print(f"   [OK] Collection name: {vector_store.collection_name}")

        # Check if collection exists
        print("\n2. Checking collection...")
        exists = vector_store.collection_exists()
        print(f"   [OK] Collection exists: {exists}")

        # Get collection count
        print("\n3. Getting document count...")
        count = vector_store.get_collection_count()
        print(f"   [OK] Document count: {count}")

        # Test clear functionality
        print("\n4. Testing clear functionality...")
        vector_store.clear_collection()
        count_after_clear = vector_store.get_collection_count()
        print(f"   [OK] Document count after clear: {count_after_clear}")

        # Test reset functionality
        print("\n5. Testing reset functionality...")
        vector_store.reset_collection()
        count_after_reset = vector_store.get_collection_count()
        print(f"   [OK] Document count after reset: {count_after_reset}")

        print("\n" + "=" * 50)
        print("[SUCCESS] Chroma vector store initialized successfully!")
        return True

    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = init_chroma_db()
    sys.exit(0 if success else 1)

