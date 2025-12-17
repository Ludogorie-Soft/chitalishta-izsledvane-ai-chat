"""
Verification script for database models.
Run this script to verify that Chitalishte and InformationCard models work correctly.
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("chcp 65001 > nul 2>&1")

from app.db.database import get_db
from app.db.models import Chitalishte, InformationCard


def test_models():
    """Test database models and relationships."""
    print("=" * 60)
    print("Database Models Verification")
    print("=" * 60)

    db = next(get_db())

    try:
        # Test 1: Query Chitalishte records
        print("\n[Test 1] Querying Chitalishte records...")
        chitalishte_count = db.query(Chitalishte).count()
        print(f"[OK] Found {chitalishte_count} Chitalishte records")

        if chitalishte_count == 0:
            print("[WARNING] No Chitalishte records found in database")
            return

        # Test 2: Get first Chitalishte with details
        print("\n[Test 2] Getting first Chitalishte details...")
        first_chitalishte = db.query(Chitalishte).first()
        print(f"[OK] Chitalishte ID: {first_chitalishte.id}")
        print(f"  Name: {first_chitalishte.name}")
        print(f"  Registration Number: {first_chitalishte.registration_number}")
        print(f"  Region: {first_chitalishte.region}")
        print(f"  Town: {first_chitalishte.town}")
        print(f"  Status: {first_chitalishte.status}")

        # Test 3: Query InformationCard records
        print("\n[Test 3] Querying InformationCard records...")
        card_count = db.query(InformationCard).count()
        print(f"[OK] Found {card_count} InformationCard records")

        # Test 4: Test relationship - Chitalishte -> InformationCards
        print("\n[Test 4] Testing relationship: Chitalishte -> InformationCards...")
        info_cards = first_chitalishte.information_cards
        print(f"[OK] Chitalishte {first_chitalishte.id} has {len(info_cards)} information cards")

        if info_cards:
            first_card = info_cards[0]
            print(f"  First card ID: {first_card.id}")
            print(f"  First card Year: {first_card.year}")
            print(f"  First card Chitalishte ID: {first_card.chitalishte_id}")

            # Verify relationship
            if first_card.chitalishte_id == first_chitalishte.id:
                print("  [OK] Relationship verified: card.chitalishte_id matches chitalishte.id")
            else:
                print("  [ERROR] Relationship error: card.chitalishte_id does not match")
                return False

        # Test 5: Test reverse relationship - InformationCard -> Chitalishte
        print("\n[Test 5] Testing reverse relationship: InformationCard -> Chitalishte...")
        if info_cards:
            card = info_cards[0]
            related_chitalishte = card.chitalishte
            print(f"[OK] InformationCard {card.id} belongs to Chitalishte {related_chitalishte.id}")
            print(f"  Chitalishte Name: {related_chitalishte.name}")

            if related_chitalishte.id == first_chitalishte.id:
                print("  [OK] Reverse relationship verified")
            else:
                print("  [ERROR] Reverse relationship error")
                return False

        # Test 6: Query with filters
        print("\n[Test 6] Testing filtered queries...")
        if first_chitalishte.region:
            filtered = (
                db.query(Chitalishte).filter(Chitalishte.region == first_chitalishte.region).count()
            )
            print(
                f"[OK] Found {filtered} Chitalishte records in region '{first_chitalishte.region}'"
            )

        # Test 7: Query InformationCards by year
        if info_cards and info_cards[0].year:
            year = info_cards[0].year
            cards_by_year = db.query(InformationCard).filter(InformationCard.year == year).count()
            print(f"[OK] Found {cards_by_year} InformationCard records for year {year}")

        # Test 8: Query Chitalishte with specific InformationCard
        print("\n[Test 7] Testing query with join...")
        chitalishte_with_cards = (
            db.query(Chitalishte)
            .join(InformationCard)
            .filter(InformationCard.year.isnot(None))
            .distinct()
            .count()
        )
        print(f"[OK] Found {chitalishte_with_cards} Chitalishte records with information cards")

        print("\n" + "=" * 60)
        print("[SUCCESS] All tests passed! Models are working correctly.")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n[ERROR] Error during testing: {str(e)}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = test_models()
    sys.exit(0 if success else 1)
