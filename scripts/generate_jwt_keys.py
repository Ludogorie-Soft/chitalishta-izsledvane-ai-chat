"""Generate RSA key pair for JWT token signing/verification.

This script generates a 2048-bit RSA key pair and prints them in a format
suitable for copying to your .env file.
"""

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization


def generate_rsa_keys():
    """Generate RSA key pair and return as PEM strings."""
    # Generate private key
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Serialize private key to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    # Serialize public key to PEM format
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )

    return private_pem, public_pem


def main():
    """Generate and print RSA keys."""
    print("=" * 70)
    print("JWT RSA Key Pair Generator")
    print("=" * 70)
    print()
    print("Generating 2048-bit RSA key pair...")
    print()

    private_pem, public_pem = generate_rsa_keys()

    print("Copy these lines to your .env file:")
    print()
    print("-" * 70)
    # Format for python-dotenv: use escaped newlines
    private_key_escaped = private_pem.replace("\n", "\\n")
    public_key_escaped = public_pem.replace("\n", "\\n")
    print(f'JWT_RSA_PRIVATE_KEY="{private_key_escaped}"')
    print()
    print(f'JWT_RSA_PUBLIC_KEY="{public_key_escaped}"')
    print("-" * 70)
    print()
    print("Note: The keys are formatted with escaped newlines (\\n) which")
    print("      python-dotenv can parse correctly.")
    print()
    print("Note: After adding these keys to .env, restart your server.")
    print("      Existing tokens will become invalid - you'll need to login again.")


if __name__ == "__main__":
    main()
