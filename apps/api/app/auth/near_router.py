"""
NEAR wallet auth — NEP-413 signature verification.

Flow:
  1. POST /auth/near/nonce  → returns a one-time 32-byte nonce (base64)
  2. Frontend calls wallet.signMessage({ message, nonce, recipient })
  3. POST /auth/near/verify → verifies ed25519 sig, issues JWT (sub=near:<account_id>)
"""

import hashlib
import base64
import secrets
import struct
import logging
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from jose import jwt as jose_jwt

from app.core.config import settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/auth/near', tags=['auth'])

_NEAR_RPC: dict[str, str] = {
    'testnet': 'https://rpc.testnet.near.org',
    'mainnet': 'https://rpc.mainnet.near.org',
}

# NEP-413 borsh prefix tag: 2^31 + 413
_NEP413_TAG = 2147484061

# ─── Base58 decode (no external dependency) ──────────────────────────────────

_B58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'


def _b58decode(encoded: str) -> bytes:
    n = 0
    for char in encoded:
        n = n * 58 + _B58_ALPHABET.index(char)
    buf: list[int] = []
    while n > 0:
        buf.append(n & 0xFF)
        n >>= 8
    leading = len(encoded) - len(encoded.lstrip('1'))
    raw = bytes(leading) + bytes(reversed(buf))
    # ed25519 keys are always 32 bytes — pad if needed
    return raw.rjust(32, b'\x00')[-32:]


# ─── NEP-413 borsh payload builder ───────────────────────────────────────────

def _borsh_str(s: str) -> bytes:
    b = s.encode('utf-8')
    return struct.pack('<I', len(b)) + b


def _build_nep413_payload(message: str, nonce_bytes: bytes, recipient: str) -> bytes:
    return (
        struct.pack('<I', _NEP413_TAG)
        + _borsh_str(message)
        + nonce_bytes          # exactly 32 bytes, no length prefix
        + _borsh_str(recipient)
        + b'\x00'              # Option<callback_url> = None
    )


# ─── Schemas ──────────────────────────────────────────────────────────────────

class NearNonceResponse(BaseModel):
    nonce: str  # base64-encoded 32 bytes


class NearVerifyRequest(BaseModel):
    account_id: str
    public_key: str   # "ed25519:<base58>"
    signature: str    # base64-encoded 64 bytes
    nonce: str        # base64-encoded 32 bytes — same value returned by /nonce
    message: str      # plaintext message that was signed
    recipient: str    # domain/contract passed to wallet.signMessage


class NearTokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    account_id: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post('/nonce', response_model=NearNonceResponse)
async def near_nonce() -> NearNonceResponse:
    """Generate a one-time nonce for NEP-413 message signing (TTL 5 min)."""
    nonce_bytes = secrets.token_bytes(32)
    nonce_b64 = base64.b64encode(nonce_bytes).decode()

    redis = get_redis()
    await redis.setex(f'near_nonce:{nonce_b64}', 300, '1')

    return NearNonceResponse(nonce=nonce_b64)


@router.post('/verify', response_model=NearTokenResponse)
async def near_verify(req: NearVerifyRequest) -> NearTokenResponse:
    """Verify a NEP-413 signed message and issue a JWT."""

    # 1. Consume nonce — one-time use, prevents replay attacks
    redis = get_redis()
    deleted = await redis.delete(f'near_nonce:{req.nonce}')
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid or expired nonce',
        )

    # 2. Verify the public key belongs to the claimed account via NEAR RPC
    rpc_url = _NEAR_RPC.get(settings.NEAR_NETWORK, _NEAR_RPC['testnet'])
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(rpc_url, json={
                'jsonrpc': '2.0',
                'id': 'evoagent',
                'method': 'query',
                'params': {
                    'request_type': 'view_access_keys',
                    'finality': 'final',
                    'account_id': req.account_id,
                },
            })
        rpc_data = resp.json()
        keys = rpc_data.get('result', {}).get('keys', [])
        known_keys = {k['public_key'] for k in keys}
    except Exception as exc:
        logger.error('NEAR RPC unavailable: %s', exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='NEAR RPC unavailable — try again shortly',
        )

    if req.public_key not in known_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Public key not associated with this account',
        )

    # 3. Decode inputs
    if not req.public_key.startswith('ed25519:'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Only ed25519 keys are supported',
        )

    try:
        key_bytes = _b58decode(req.public_key[len('ed25519:'):])
        sig_bytes = base64.b64decode(req.signature)
        nonce_bytes = base64.b64decode(req.nonce)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid encoding in key, signature, or nonce',
        )

    if len(nonce_bytes) != 32:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Nonce must decode to exactly 32 bytes',
        )

    # 4. Verify NEP-413 ed25519 signature
    borsh_payload = _build_nep413_payload(req.message, nonce_bytes, req.recipient)
    digest = hashlib.sha256(borsh_payload).digest()

    try:
        pub_key = Ed25519PublicKey.from_public_bytes(key_bytes)
        pub_key.verify(sig_bytes, digest)
    except InvalidSignature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Signature verification failed',
        )

    # 5. Issue JWT — sub = "near:<account_id>" to distinguish from email auth
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    token = jose_jwt.encode(
        {'sub': f'near:{req.account_id}', 'exp': expire},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    return NearTokenResponse(access_token=token, account_id=req.account_id)
