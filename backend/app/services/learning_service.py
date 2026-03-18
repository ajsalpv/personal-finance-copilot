import logging
from typing import List, Optional, Dict
from sqlalchemy import text
from app.database import async_session_factory

logger = logging.getLogger(__name__)

async def get_progress(db, user_id: str, language: str) -> Optional[Dict]:
    """Retrieves user's learning progress for a specific language."""
    result = await db.execute(
        text("SELECT current_level, total_words_learned, daily_streak, points FROM user_learning_progress WHERE user_id = :uid AND language = :lang"),
        {"uid": user_id, "lang": language}
    )
    row = result.fetchone()
    if row:
        return {
            "current_level": row[0],
            "total_words_learned": row[1],
            "daily_streak": row[2],
            "points": row[3]
        }
    return None

async def add_vocabulary(db, user_id: str, language: str, word: str, translation: str):
    """Adds a new word to the user's vocabulary and updates total count."""
    # First insert or ignore vocab
    await db.execute(
        text("INSERT INTO vocabulary (user_id, language, word, translation) VALUES (:uid, :lang, :word, :trans) ON CONFLICT DO NOTHING"),
        {"uid": user_id, "lang": language, "word": word, "trans": translation}
    )
    # Increment total words learned
    await db.execute(
        text("INSERT INTO user_learning_progress (user_id, language, total_words_learned, points) VALUES (:uid, :lang, 1, 10) "
             "ON CONFLICT (user_id, language) DO UPDATE SET total_words_learned = user_learning_progress.total_words_learned + 1, points = user_learning_progress.points + 10"),
        {"uid": user_id, "lang": language}
    )
    await db.commit()

async def record_lesson(db, user_id: str, language: str, lesson_type: str, score: int):
    """Records a lesson and updates streak/points."""
    await db.execute(
        text("INSERT INTO learning_lessons (user_id, language, lesson_type, performance_score) VALUES (:uid, :lang, :type, :score)"),
        {"uid": user_id, "lang": language, "type": lesson_type, "score": score}
    )
    # Update points and potentially level
    await db.execute(
        text("INSERT INTO user_learning_progress (user_id, language, points, last_lesson_at) VALUES (:uid, :lang, :pts, NOW()) "
             "ON CONFLICT (user_id, language) DO UPDATE SET points = user_learning_progress.points + :pts, last_lesson_at = NOW()"),
        {"uid": user_id, "lang": language, "pts": score}
    )
    await db.commit()
