r"""Smoke-test every backend component in isolation.

Run:  .\.venv\Scripts\python.exe smoke_test.py

Each check prints PASS/FAIL with a short detail. Exits non-zero if any fail.
"""
import asyncio
import sys
import time
import traceback

from dotenv import load_dotenv

load_dotenv()


RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {name}  {detail}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# ---------- 1. audio_utils ----------
def test_audio_utils() -> None:
    section("audio_utils")
    try:
        from audio_utils import mulaw8k_to_pcm16k, pcm_to_mulaw8k, rms_dbfs, chunk_bytes

        # silence: 160 bytes of μ-law silence (0xFF is μ-law zero)
        silence_mulaw = b"\xff" * 160
        pcm16k = mulaw8k_to_pcm16k(silence_mulaw)
        # 8k→16k upsample doubles sample count; PCM16 is 2 bytes/sample.
        # audioop.ratecv loses one sample on the first call (no carry state),
        # so accept the ideal 640 or the ratecv-trimmed 638.
        expected = {640, 638}
        record(
            "mulaw->pcm length (~2x upsample)",
            len(pcm16k) in expected,
            f"got {len(pcm16k)} bytes (expected 638 or 640)",
        )

        # rms of silence should be very low (-100 dBFS-ish)
        db_silence = rms_dbfs(pcm16k)
        record("rms_dbfs(silence) is very quiet", db_silence < -60, f"{db_silence:.1f} dBFS")

        # roundtrip: μ-law -> PCM16k -> μ-law8k should preserve length ratio
        back = pcm_to_mulaw8k(pcm16k, src_rate=16000)
        record(
            "pcm->mulaw roundtrip length",
            len(back) == 160,
            f"got {len(back)} expected 160",
        )

        # chunk_bytes
        chunks = list(chunk_bytes(b"x" * 500, 160))
        record("chunk_bytes(500,160) -> 4 chunks", len(chunks) == 4, f"got {len(chunks)}")
    except Exception:
        record("audio_utils crashed", False, traceback.format_exc(limit=2))


# ---------- 2. aviationstack ----------
async def test_aviationstack() -> None:
    section("aviationstack")
    try:
        from aviation_client import get_flight_status

        # Try a common flight code; if not flying right now, "found": False is still a PASS
        t0 = time.time()
        result = await get_flight_status("AI302")
        dt = (time.time() - t0) * 1000
        if "found" in result:
            detail = f"found={result['found']} status={result.get('status')} ({dt:.0f}ms)"
            record("get_flight_status('AI302') reachable", True, detail)
        else:
            record("get_flight_status returned unexpected shape", False, repr(result))
    except Exception:
        record("aviationstack call failed", False, traceback.format_exc(limit=2))


# ---------- 3. Sarvam TTS ----------
async def test_sarvam_tts() -> bytes | None:
    section("Sarvam TTS")
    try:
        from sarvam_client import tts_synthesize

        t0 = time.time()
        pcm = await tts_synthesize("Hello, this is a backend smoke test.")
        dt = (time.time() - t0) * 1000
        if pcm and len(pcm) > 1000:
            duration_s = len(pcm) / 2 / 22050
            record(
                "tts_synthesize returned PCM",
                True,
                f"{len(pcm)} bytes (~{duration_s:.2f}s audio, {dt:.0f}ms api)",
            )
            return pcm
        record("tts_synthesize returned too little audio", False, f"len={len(pcm) if pcm else 0}")
    except Exception:
        record("Sarvam TTS crashed", False, traceback.format_exc(limit=2))
    return None


# ---------- 4. Sarvam STT (round-trip from TTS) ----------
async def test_sarvam_stt(tts_pcm22050: bytes | None) -> None:
    section("Sarvam STT")
    if not tts_pcm22050:
        record("STT skipped (no TTS audio to feed)", False, "")
        return
    try:
        import audioop
        from sarvam_client import stt_transcribe

        # TTS gives PCM16 @ 22050Hz; STT wants PCM16 @ 16000Hz
        pcm16k, _ = audioop.ratecv(tts_pcm22050, 2, 1, 22050, 16000, None)

        t0 = time.time()
        text = await stt_transcribe(pcm16k)
        dt = (time.time() - t0) * 1000
        if text:
            record("stt_transcribe returned text", True, f"'{text}' ({dt:.0f}ms)")
        else:
            record("stt_transcribe returned empty string", False, "")
    except Exception:
        record("Sarvam STT crashed", False, traceback.format_exc(limit=2))


# ---------- 5. OpenAI plain reply ----------
async def test_openai_plain() -> None:
    section("OpenAI (no tool)")
    try:
        from openai_client import answer

        t0 = time.time()
        reply = await answer("Hi, can you remind me what you can help with?", [])
        dt = (time.time() - t0) * 1000
        if reply and len(reply) > 5:
            preview = reply[:120].replace("\n", " ")
            record("answer() returned a reply", True, f"'{preview}...' ({dt:.0f}ms)")
        else:
            record("answer() returned empty/short reply", False, f"'{reply}'")
    except Exception:
        record("OpenAI plain crashed", False, traceback.format_exc(limit=2))


# ---------- 6. OpenAI with aviation tool call ----------
async def test_openai_tool() -> None:
    section("OpenAI (with aviationstack tool)")
    try:
        from openai_client import answer

        t0 = time.time()
        reply = await answer("Can you check the status of flight AI302 for me?", [])
        dt = (time.time() - t0) * 1000
        if reply and len(reply) > 5:
            preview = reply[:200].replace("\n", " ")
            record("tool-call flow returned a reply", True, f"'{preview}...' ({dt:.0f}ms)")
        else:
            record("tool-call flow returned empty reply", False, f"'{reply}'")
    except Exception:
        record("OpenAI tool-call crashed", False, traceback.format_exc(limit=2))


async def main() -> int:
    print("Backend smoke test — aviation-voice-demo\n")

    test_audio_utils()
    await test_aviationstack()
    tts_pcm = await test_sarvam_tts()
    await test_sarvam_stt(tts_pcm)
    await test_openai_plain()
    await test_openai_tool()

    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n=== Summary: {passed}/{total} passed ===")
    for name, ok, detail in RESULTS:
        if not ok:
            print(f"  FAIL: {name}  {detail}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
