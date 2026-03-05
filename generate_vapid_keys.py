"""
Run once to generate VAPID key pair for Web Push notifications.
Then add the output to your .env file.

Usage:
    python generate_vapid_keys.py
"""
from py_vapid import Vapid
import base64


def generate():
    vapid = Vapid()
    vapid.generate_keys()

    # Private key in PEM format (for pywebpush)
    private_pem = vapid.private_pem().decode().strip()

    # Public key in base64url uncompressed format (for browser subscription)
    public_bytes = vapid.public_key.public_bytes(
        __import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding", "PublicFormat"])
        .Encoding.X962,
        __import__("cryptography.hazmat.primitives.serialization", fromlist=["Encoding", "PublicFormat"])
        .PublicFormat.UncompressedPoint,
    )
    public_b64 = base64.urlsafe_b64encode(public_bytes).rstrip(b"=").decode()

    print("Add these to your .env file:\n")
    print(f'VAPID_PUBLIC_KEY="{public_b64}"')
    print(f'VAPID_PRIVATE_KEY="{private_pem}"')


if __name__ == "__main__":
    generate()
