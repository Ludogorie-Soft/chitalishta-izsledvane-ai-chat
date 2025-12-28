"""Create a new user in the database with hashed password."""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import bcrypt
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import User


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Note: bcrypt has a 72-byte limit. Passwords longer than 72 bytes will be truncated.
    """
    # Encode password to bytes
    password_bytes = password.encode("utf-8")

    # Check length (bcrypt limit is 72 bytes)
    if len(password_bytes) > 72:
        print(f"Warning: Password is {len(password_bytes)} bytes, truncating to 72 bytes (bcrypt limit)")
        password_bytes = password_bytes[:72]

    # Generate salt and hash
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password_bytes, salt)

    # Return as string (bcrypt hash includes the salt)
    return password_hash.decode("utf-8")


def create_user(username: str, password: str, email: str = None, role: str = "administrator") -> User:
    """
    Create a new user in the database.

    Args:
        username: Username for login
        password: Plain text password (will be hashed)
        email: Optional email address
        role: User role (default: 'administrator')

    Returns:
        Created User object
    """
    db: Session = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"User '{username}' already exists. Updating password and role...")
            # Update existing user
            existing_user.password_hash = hash_password(password)
            existing_user.role = role
            existing_user.is_active = True
            if email:
                existing_user.email = email
            db.commit()
            db.refresh(existing_user)
            print(f"✓ User '{username}' updated successfully!")
            print(f"  Role: {role}")
            print(f"  Email: {existing_user.email or '(not set)'}")
            print(f"  Active: {existing_user.is_active}")
            return existing_user

        if email:
            existing_email = db.query(User).filter(User.email == email).first()
            if existing_email:
                raise ValueError(f"User with email '{email}' already exists")

        # Hash password
        password_hash = hash_password(password)

        # Create user
        user = User(
            username=username,
            password_hash=password_hash,
            email=email,
            role=role,
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        print(f"✓ User '{username}' created successfully!")
        print(f"  Role: {role}")
        print(f"  Email: {email or '(not set)'}")
        print(f"  Active: {user.is_active}")

        return user
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    """Interactive user creation."""
    if len(sys.argv) < 3:
        print("Usage: python scripts/create_user.py <username> <password> [email] [role]")
        print("\nExample:")
        print("  python scripts/create_user.py admin mypassword123 admin@example.com administrator")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else None
    role = sys.argv[4] if len(sys.argv) > 4 else "administrator"

    try:
        create_user(username, password, email, role)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error creating user: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

