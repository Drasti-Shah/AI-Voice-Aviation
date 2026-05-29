import audioop
import numpy as np


def mulaw8k_to_pcm16k(mulaw_bytes: bytes) -> bytes:
    """Twilio inbound: μ-law 8kHz → linear PCM16 16kHz (for Sarvam STT)."""
    pcm8k = audioop.ulaw2lin(mulaw_bytes, 2)
    pcm16k, _ = audioop.ratecv(pcm8k, 2, 1, 8000, 16000, None)
    return pcm16k


def pcm_to_mulaw8k(pcm_bytes: bytes, src_rate: int) -> bytes:
    """Sarvam TTS PCM16 @ src_rate → μ-law 8kHz (for Twilio outbound)."""
    if src_rate != 8000:
        pcm8k, _ = audioop.ratecv(pcm_bytes, 2, 1, src_rate, 8000, None)
    else:
        pcm8k = pcm_bytes
    return audioop.lin2ulaw(pcm8k, 2)


def chunk_bytes(data: bytes, size: int):
    for i in range(0, len(data), size):
        yield data[i : i + size]


def rms_dbfs(pcm16: bytes) -> float:
    """RMS volume of PCM16 audio in dBFS. Used for simple silence detection."""
    if not pcm16:
        return -120.0
    arr = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32)
    if arr.size == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(arr * arr)) + 1e-9)
    return 20.0 * np.log10(rms / 32768.0 + 1e-9)
