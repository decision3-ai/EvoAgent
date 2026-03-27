import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    FastAPI dependency: extracts the NEAR accountId from the Authorization header.
    The frontend sends the NEAR wallet accountId as the Bearer token.
    """
    account_id = credentials.credentials.strip()
    if not account_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing account ID',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return account_id
