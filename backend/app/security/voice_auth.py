"""
Nova AI Life Assistant — Voice Fingerprint Authentication

Uses resemblyzer to create speaker embeddings from voice samples.
Enrollment: user provides 3+ voice clips → averaged embedding stored.
Verification: new voice clip embedding compared via cosine similarity.
"""
import io
import numpy as np
from typing import List, Optional

from app.config import get_settings

# Lazy-load resemblyzer to avoid import overhead when not needed
_encoder = None


def _get_encoder():
    global _encoder
    if _encoder is None:
        from resemblyzer import VoiceEncoder
        _encoder = VoiceEncoder()
    return _encoder


def _preprocess_audio(audio_bytes: bytes) -> np.ndarray:
    """Convert audio bytes to numpy array (mono, 16kHz)."""
    import soundfile as sf
    audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_data = np.mean(audio_data, axis=1)
    # Resample to 16kHz if needed
    if sample_rate != 16000:
        import librosa
        audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
    return audio_data.astype(np.float32)


def create_voice_embedding(audio_samples: List[bytes]) -> np.ndarray:
    """
    Create a reference voice embedding from multiple audio samples.
    Returns a 256-dimensional numpy array (the speaker's voiceprint).
    """
    encoder = _get_encoder()
    from resemblyzer import preprocess_wav

    embeddings = []
    for sample in audio_samples:
        wav = _preprocess_audio(sample)
        wav = preprocess_wav(wav)
        embedding = encoder.embed_utterance(wav)
        embeddings.append(embedding)

    # Average all embeddings for a robust reference
    reference = np.mean(embeddings, axis=0)
    # Normalize
    reference = reference / np.linalg.norm(reference)
    return reference


def verify_voice(audio_bytes: bytes, reference_embedding: np.ndarray) -> tuple[bool, float]:
    """
    Verify a voice sample against a reference embedding.
    Returns (is_verified, similarity_score).
    """
    encoder = _get_encoder()
    from resemblyzer import preprocess_wav

    wav = _preprocess_audio(audio_bytes)
    wav = preprocess_wav(wav)
    test_embedding = encoder.embed_utterance(wav)
    test_embedding = test_embedding / np.linalg.norm(test_embedding)

    # Cosine similarity
    similarity = float(np.dot(reference_embedding, test_embedding))

    threshold = get_settings().VOICE_SIMILARITY_THRESHOLD
    return similarity >= threshold, similarity


def embedding_to_bytes(embedding: np.ndarray) -> bytes:
    """Serialize a numpy embedding to bytes for database storage."""
    return embedding.tobytes()


def bytes_to_embedding(data: bytes) -> np.ndarray:
    """Deserialize bytes back to a numpy embedding."""
    return np.frombuffer(data, dtype=np.float32)
