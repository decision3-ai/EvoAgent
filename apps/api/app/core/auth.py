import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Dual-mode auth dependency.

    - JWT token (starts with 'eyJ'): issued by /api/v1/auth/login — returns email as user_id.
    - Anything else: treated as NEAR accountId (legacy V1 behaviour) — returned as-is.
    """
    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing token',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    if token.startswith('eyJ'):
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id: str | None = payload.get('sub')
            if not user_id:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')
            return user_id
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token expired or invalid',
                headers={'WWW-Authenticate': 'Bearer'},
            )

    # NEAR accountId path — accept as-is (no signature validation in V1)
    return token
