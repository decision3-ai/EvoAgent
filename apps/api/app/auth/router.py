from datetime import datetime, timedelta

import bcrypt

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt

from app.core.config import settings
from app.core.database import get_db
from app.auth.models import User
from app.auth.schemas import RegisterRequest, LoginRequest, TokenResponse
from app.chat.d3rcp_client import trigger_x402_payment
import asyncio

router = APIRouter(prefix='/auth', tags=['auth'])


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_jwt(email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {'sub': email, 'exp': expire},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


@router.post('/register', response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail='Email already registered')

    user = User(email=payload.email, hashed_password=_hash_password(payload.password))
    db.add(user)
    await db.commit()

    asyncio.create_task(trigger_x402_payment(f"register-{user.id}", payload.email, 0))
    return TokenResponse(access_token=_create_jwt(payload.email), email=payload.email)


@router.post('/login', response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not _verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid email or password',
        )

    asyncio.create_task(trigger_x402_payment(f"login-{user.id}", payload.email, 0))
    return TokenResponse(access_token=_create_jwt(payload.email), email=payload.email)
