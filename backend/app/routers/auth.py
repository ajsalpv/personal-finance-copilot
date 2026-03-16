"""
Auth Router — Registration, Login, Voice Enrollment & Verification.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.security.auth import (
    hash_password, verify_password, create_access_token, get_current_user,
)
from app.security.voice_auth import (
    create_voice_embedding, verify_voice, embedding_to_bytes, bytes_to_embedding,
)
from app.schemas.user import (
    UserRegister, UserLogin, UserResponse, TokenResponse,
    VoiceEnrollResponse, VoiceVerifyResponse,
)

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(body: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    try:
        # Check if email already exists
        existing = await db.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": body.email},
        )
        if existing.first():
            raise HTTPException(status_code=400, detail="Email already registered")

        # Create user
        hashed = hash_password(body.password)
        result = await db.execute(
            text("""
                INSERT INTO users (name, email, password_hash, telegram_id)
                VALUES (:name, :email, :hash, :telegram_id)
                RETURNING id, name, email, telegram_id, created_at
            """),
            {
                "name": body.name, "email": body.email,
                "hash": hashed, "telegram_id": body.telegram_id,
            },
        )
        await db.commit()
        user = result.mappings().first()

        # Copy default categories for this user
        await db.execute(
            text("""
                INSERT INTO categories (user_id, name, type, icon, is_default)
                SELECT :user_id, name, type, icon, is_default
                FROM categories WHERE user_id IS NULL
            """),
            {"user_id": str(user["id"])},
        )
        await db.commit()

        token = create_access_token({"sub": str(user["id"])})
        return TokenResponse(
            access_token=token,
            user=UserResponse(
                id=str(user["id"]),
                name=user["name"],
                email=user["email"],
                telegram_id=user["telegram_id"],
                created_at=user["created_at"],
            ),
        )
    except Exception as e:
        import traceback
        err_str = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"CRASH: {str(e)} | Tr: {err_str}")


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and get JWT token."""
    result = await db.execute(
        text("SELECT id, name, email, telegram_id, password_hash, created_at FROM users WHERE email = :email"),
        {"email": body.email},
    )
    user = result.mappings().first()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user["id"])})
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=str(user["id"]),
            name=user["name"],
            email=user["email"],
            telegram_id=user["telegram_id"],
            created_at=user["created_at"],
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return UserResponse(
        id=str(current_user["id"]),
        name=current_user["name"],
        email=current_user["email"],
        telegram_id=current_user.get("telegram_id"),
        created_at=current_user["created_at"],
    )


@router.post("/voice/enroll", response_model=VoiceEnrollResponse)
async def enroll_voice(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enroll voice fingerprint. Upload 3+ voice samples (.wav or .mp3).
    The system will create a reference embedding from the averaged samples.
    """
    if len(files) < 3:
        raise HTTPException(
            status_code=400,
            detail="Please upload at least 3 voice samples for reliable enrollment",
        )

    samples = []
    for f in files:
        content = await f.read()
        samples.append(content)

    embedding = create_voice_embedding(samples)
    embedding_bytes = embedding_to_bytes(embedding)

    await db.execute(
        text("UPDATE users SET voice_embedding = :emb WHERE id = :id"),
        {"emb": embedding_bytes, "id": str(current_user["id"])},
    )
    await db.commit()

    return VoiceEnrollResponse(
        message="Voice fingerprint enrolled successfully",
        samples_processed=len(samples),
    )


@router.post("/voice/verify", response_model=VoiceVerifyResponse)
async def verify_voice_endpoint(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a voice sample against the enrolled fingerprint."""
    # Get stored embedding
    result = await db.execute(
        text("SELECT voice_embedding FROM users WHERE id = :id"),
        {"id": str(current_user["id"])},
    )
    row = result.first()
    if not row or not row[0]:
        raise HTTPException(
            status_code=400,
            detail="No voice fingerprint enrolled. Use /auth/voice/enroll first.",
        )

    reference = bytes_to_embedding(row[0])
    audio_content = await file.read()
    is_verified, similarity = verify_voice(audio_content, reference)

    return VoiceVerifyResponse(verified=is_verified, similarity=round(similarity, 4))
