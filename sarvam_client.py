import os
import io
import base64
import wave
import httpx

SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


def _pcm16_to_wav_bytes(pcm16: bytes, sample_rate: int = 16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm16)
    return buf.getvalue()


async def stt_transcribe(pcm16_16k: bytes) -> str:
    """Send 16-bit PCM @ 16kHz mono to Sarvam STT, return English transcript."""
    api_key = os.environ["SARVAM_API_KEY"]
    wav_bytes = _pcm16_to_wav_bytes(pcm16_16k, sample_rate=16000)

    files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
    data = {
        "model": "saarika:v2.5",
        "language_code": "en-IN",
        "with_timestamps": "false",
    }
    headers = {"api-subscription-key": api_key}

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(SARVAM_STT_URL, headers=headers, data=data, files=files)
        r.raise_for_status()
        return (r.json().get("transcript") or "").strip()


async def tts_synthesize(text: str) -> bytes:
    """Synthesize English text via Sarvam Bulbul, return 16-bit PCM @ 22050Hz mono."""
    api_key = os.environ["SARVAM_API_KEY"]
    headers = {"api-subscription-key": api_key, "Content-Type": "application/json"}
    payload = {
        "inputs": [text[:1500]],
        "target_language_code": "en-IN",
        "speaker": "anushka",
        "model": "bulbul:v2",
        "speech_sample_rate": 22050,
        "enable_preprocessing": True,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(SARVAM_TTS_URL, headers=headers, json=payload)
        r.raise_for_status()
        b64 = r.json()["audios"][0]
        wav_bytes = base64.b64decode(b64)

    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        return wf.readframes(wf.getnframes())
