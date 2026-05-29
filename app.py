import os
import io
import csv
import json
import time
import uuid
import base64
import asyncio
import logging
import random

from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import PlainTextResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from twilio.rest import Client as TwilioClient

from audio_utils import mulaw8k_to_pcm16k, pcm_to_mulaw8k, chunk_bytes, rms_dbfs
from sarvam_client import stt_transcribe, tts_synthesize
from openai_client import answer

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("aviation-demo")

app = FastAPI()

# CORS origins. Defaults to local Next.js dev; in production set CORS_ORIGINS to
# a comma-separated list of allowed origins (e.g. your deployed frontend URL).
_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_cors_origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", _default_origins).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Per-call data, keyed by Twilio call SID.
#   call_meta[sid]   = {"sid","to","from","started","ended","duration","status","campaign_id"}
#   call_turns[sid]  = [{"role","text","ts"}, ...]
#   call_metrics[sid]= {"tool_calls": int, "user_turns": int, "bot_turns": int, "avg_response_ms": float}
call_meta: dict[str, dict] = {}
call_turns: dict[str, list[dict]] = {}
call_metrics: dict[str, dict] = {}

# Active call SID currently streaming (the most recent one to send a "start"
# event). Used only as the default "foreground" for /api/transcript polling
# — never as the source of truth for which call a turn belongs to.
active_call_sid: str | None = None

# Campaigns: id -> {"id","name","created","numbers","calls","status","cursor"}
campaigns: dict[str, dict] = {}

# Disk persistence so state survives restart.
STATE_FILE = os.path.join(os.path.dirname(__file__), "_state.json")
_save_lock = asyncio.Lock()


def _save_state_sync() -> None:
    try:
        data = {
            "call_meta": call_meta,
            "call_turns": call_turns,
            "call_metrics": call_metrics,
            "campaigns": campaigns,
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, default=str)
    except Exception:
        log.exception("save state failed")


def _load_state() -> None:
    if not os.path.exists(STATE_FILE):
        return
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        call_meta.update(data.get("call_meta", {}))
        call_turns.update(data.get("call_turns", {}))
        call_metrics.update(data.get("call_metrics", {}))
        campaigns.update(data.get("campaigns", {}))
        # Any campaign that was running mid-restart can't be resumed — mark paused.
        for c in campaigns.values():
            if c.get("status") == "running":
                c["status"] = "paused"
    except Exception:
        # Bad state file? Ignore rather than crash.
        pass


def _record(call_sid: str | None, role: str, text: str) -> None:
    """Record a turn into the per-call store. call_sid is REQUIRED so we
    can't accidentally write a turn from call A into call B's transcript."""
    entry = {"role": role, "text": text, "ts": time.time()}
    if call_sid:
        call_turns.setdefault(call_sid, []).append(entry)
        m = call_metrics.setdefault(call_sid, {"user_turns": 0, "bot_turns": 0, "tool_calls": 0})
        if role == "user":
            m["user_turns"] += 1
        elif role == "bot":
            m["bot_turns"] += 1


GREETING = "Hi! This is the airline assistant. You can ask me about a flight's status or about baggage and check-in. How can I help?"

# Played in parallel with the tool call + second LLM call (~3s) so the caller
# hears the bot start responding within ~1s instead of sitting in silence.
TOOL_FILLERS = [
    "Let me check that for you.",
    "One moment, looking that up.",
    "Just a second.",
    "Checking that now.",
    "Sure, pulling that up.",
]

# Silence detection (server-side VAD-lite)
SILENCE_DBFS = -45.0       # below this is "silence"
SILENCE_HANG_MS = 700      # how long of silence ends a user turn
MIN_UTTERANCE_MS = 400     # ignore micro-blips
FRAME_MS = 20              # Twilio sends 20ms frames


@app.get("/", response_class=PlainTextResponse)
async def health():
    return "ok"


@app.post("/voice")
async def voice_webhook(request: Request):
    """Twilio Voice webhook — returns TwiML that connects the call to our Media Stream."""
    raw = os.environ.get("PUBLIC_HOST", request.url.hostname).strip()
    parsed = urlparse(raw if "://" in raw else f"//{raw}", scheme="", allow_fragments=False)
    host = parsed.netloc or raw.split("/", 1)[0]
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://{host}/stream" />
  </Connect>
</Response>"""
    return PlainTextResponse(content=twiml, media_type="application/xml")


CHUNK_MS = 100                    # send 100ms of audio per WS message
CHUNK_BYTES = 8 * CHUNK_MS        # μ-law 8kHz = 8 bytes per ms
CHUNK_SECONDS = CHUNK_MS / 1000.0


async def _speak(ws: WebSocket, stream_sid: str, text: str, call_sid: str | None = None):
    """TTS -> μ-law 8kHz -> stream back to Twilio in CHUNK_MS chunks.
    Paced against an absolute monotonic clock so per-frame sleep jitter
    doesn't accumulate into audio gaps. Silently returns if the websocket
    is closed mid-send (caller hung up)."""
    log.info("BOT: %s", text)
    _record(call_sid, "bot", text)
    try:
        pcm22 = await tts_synthesize(text)
    except Exception:
        log.exception("TTS failed")
        return
    mulaw = pcm_to_mulaw8k(pcm22, src_rate=22050)

    loop = asyncio.get_event_loop()
    start = loop.time()
    try:
        for i, chunk in enumerate(chunk_bytes(mulaw, CHUNK_BYTES)):
            await ws.send_text(json.dumps({
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": base64.b64encode(chunk).decode("ascii")},
            }))
            # Sleep until next absolute slot, not a fixed relative delay.
            # On Windows, asyncio.sleep granularity is ~15ms, so relative
            # sleeps drift; absolute targets self-correct.
            target = start + (i + 1) * CHUNK_SECONDS
            delay = target - loop.time()
            if delay > 0:
                await asyncio.sleep(delay)
    except (WebSocketDisconnect, RuntimeError):
        # Caller hung up mid-utterance; nothing to recover.
        return


@app.websocket("/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    log.info("WS connected")

    stream_sid: str | None = None
    call_sid: str | None = None  # this handler's OWN call SID (not the global)
    history: list[dict] = []
    pcm16_buf = bytearray()
    silence_ms = 0
    voiced_ms = 0
    # One task covers thinking + speaking. While it's running, incoming
    # audio is dropped so the bot never talks over itself or trips a
    # spurious second turn from its own echo.
    busy_task: asyncio.Task | None = None

    async def handle_turn(utterance_pcm16_16k: bytes) -> None:
        try:
            transcript = await stt_transcribe(utterance_pcm16_16k)
            if not transcript:
                return
            log.info("USER: %s", transcript)
            _record(call_sid, "user", transcript)

            async def play_filler() -> None:
                await _speak(ws, stream_sid, random.choice(TOOL_FILLERS), call_sid=call_sid)

            reply = await answer(transcript, history, on_tool_call=play_filler)
            if not reply:
                reply = "Sorry, I didn't catch that. Could you say that again?"

            history.append({"role": "user", "content": transcript})
            history.append({"role": "assistant", "content": reply})
            del history[:-12]

            await _speak(ws, stream_sid, reply, call_sid=call_sid)
        except Exception:
            log.exception("turn error")

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            event = msg.get("event")

            if event == "start":
                global active_call_sid
                stream_sid = msg["start"]["streamSid"]
                call_sid = msg["start"].get("callSid")
                log.info("stream start sid=%s callSid=%s", stream_sid, call_sid)
                active_call_sid = call_sid  # foreground for /api/transcript polling
                if call_sid:
                    call_meta.setdefault(call_sid, {})["started"] = time.time()
                    call_meta[call_sid]["status"] = "in-progress"
                    # Start a fresh per-call transcript (don't bleed in from earlier).
                    call_turns[call_sid] = []
                    call_metrics[call_sid] = {"user_turns": 0, "bot_turns": 0, "tool_calls": 0}
                _record(call_sid, "system", "Call connected")
                busy_task = asyncio.create_task(_speak(ws, stream_sid, GREETING, call_sid=call_sid))

            elif event == "media":
                if busy_task and not busy_task.done():
                    # Discard caller audio while bot is thinking/talking so
                    # bot echo or post-speech noise can't trigger a new turn.
                    pcm16_buf.clear()
                    silence_ms = 0
                    voiced_ms = 0
                    continue

                payload_b64 = msg["media"]["payload"]
                mulaw = base64.b64decode(payload_b64)
                pcm16 = mulaw8k_to_pcm16k(mulaw)
                pcm16_buf.extend(pcm16)

                # Simple energy-based silence detection on the latest frame
                level = rms_dbfs(pcm16)
                if level < SILENCE_DBFS:
                    silence_ms += FRAME_MS
                else:
                    silence_ms = 0
                    voiced_ms += FRAME_MS

                if voiced_ms >= MIN_UTTERANCE_MS and silence_ms >= SILENCE_HANG_MS:
                    utterance = bytes(pcm16_buf)
                    pcm16_buf.clear()
                    voiced_ms = 0
                    silence_ms = 0
                    busy_task = asyncio.create_task(handle_turn(utterance))

            elif event == "stop":
                log.info("stream stop callSid=%s", call_sid)
                _record(call_sid, "system", "Call ended")
                # IMPORTANT: mark THIS handler's call complete, not whatever
                # is in the global (which may have been overwritten by a
                # concurrent call's start event).
                if call_sid and call_sid in call_meta:
                    call_meta[call_sid]["ended"] = time.time()
                    call_meta[call_sid]["status"] = "completed"
                if active_call_sid == call_sid:
                    active_call_sid = None
                _save_state_sync()
                break

    except WebSocketDisconnect:
        log.info("WS disconnected callSid=%s", call_sid)
    except Exception:
        log.exception("WS error")
    finally:
        # Safety net: if we never got a clean "stop" event (caller hung up
        # abruptly, network blip, etc.) make sure our call is still marked
        # completed so the UI doesn't show it as in-progress forever.
        if call_sid and call_sid in call_meta and call_meta[call_sid].get("status") == "in-progress":
            call_meta[call_sid]["ended"] = time.time()
            call_meta[call_sid]["status"] = "completed"
        if active_call_sid == call_sid:
            active_call_sid = None
        if busy_task and not busy_task.done():
            busy_task.cancel()
        _save_state_sync()


# ---------------------------------------------------------------------------
# JSON API for the Next.js frontend
# ---------------------------------------------------------------------------

class CallRequest(BaseModel):
    to: str


def _public_host() -> str:
    raw = os.environ["PUBLIC_HOST"].strip()
    parsed = urlparse(raw if "://" in raw else f"//{raw}", scheme="", allow_fragments=False)
    return parsed.netloc or raw.split("/", 1)[0]


def _twilio_client() -> TwilioClient:
    return TwilioClient(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])


def _place_call(to: str, campaign_id: str | None = None) -> dict:
    """Place an outbound call and seed call_meta. Returns Twilio call dict."""
    host = _public_host()
    from_number = os.environ["TWILIO_FROM_NUMBER"]
    client = _twilio_client()
    call = client.calls.create(
        to=to,
        from_=from_number,
        url=f"https://{host}/voice",
        record=True,
    )
    call_meta[call.sid] = {
        "sid": call.sid,
        "to": to,
        "from": from_number,
        "status": call.status,
        "created": time.time(),
        "started": None,
        "ended": None,
        "campaign_id": campaign_id,
    }
    return {"sid": call.sid, "status": call.status, "to": to, "from": from_number}


@app.post("/api/call")
async def api_call(req: CallRequest):
    to = req.to.strip()
    if not to.startswith("+"):
        raise HTTPException(400, "phone must be E.164 (start with '+')")
    try:
        result = _place_call(to)
    except KeyError as e:
        raise HTTPException(500, f"missing env var {e}")
    _save_state_sync()
    return result


@app.get("/api/transcript")
async def api_transcript(call_sid: str | None = None):
    """Live transcript: for the given call_sid, or the foreground active call."""
    sid = call_sid or active_call_sid
    return {"call_sid": sid, "turns": call_turns.get(sid, []) if sid else []}


@app.post("/api/transcript/reset")
async def api_transcript_reset():
    # No-op now that transcripts are per-call. Kept for frontend compatibility.
    return {"ok": True}


@app.get("/api/call/{sid}")
async def api_call_status(sid: str):
    try:
        client = _twilio_client()
        call = client.calls(sid).fetch()
    except Exception as e:
        raise HTTPException(404, f"call not found: {e}")
    info = {
        "sid": call.sid,
        "status": call.status,
        "duration": call.duration,
        "to": call.to,
        "from": call.from_formatted,
        "start_time": str(call.start_time) if call.start_time else None,
        "end_time": str(call.end_time) if call.end_time else None,
    }
    # Mirror status into our local store so the calls list reflects it.
    if sid in call_meta:
        call_meta[sid]["status"] = call.status
        if call.duration:
            call_meta[sid]["duration"] = int(call.duration)
    return info


@app.get("/api/calls")
async def api_calls_list():
    """All calls we've placed/seen this session, newest first."""
    out = []
    for sid, m in call_meta.items():
        turns = call_turns.get(sid, [])
        metrics = call_metrics.get(sid, {})
        out.append({
            **m,
            "turn_count": len(turns),
            "user_turns": metrics.get("user_turns", 0),
            "bot_turns": metrics.get("bot_turns", 0),
        })
    out.sort(key=lambda c: c.get("created", 0), reverse=True)
    return {"calls": out}


@app.get("/api/calls/{sid}/transcript")
async def api_call_transcript(sid: str):
    return {
        "sid": sid,
        "meta": call_meta.get(sid, {}),
        "metrics": call_metrics.get(sid, {}),
        "turns": call_turns.get(sid, []),
    }


@app.get("/api/calls/{sid}/recording")
async def api_call_recording(sid: str):
    """Redirect to the (auth-required) Twilio recording MP3."""
    client = _twilio_client()
    recs = client.calls(sid).recordings.list(limit=1)
    if not recs:
        raise HTTPException(404, "no recording")
    rec = recs[0]
    # Build the public MP3 URL (Basic auth via embedded creds — only works server-side).
    # The frontend can't fetch this directly because of CORS + auth, so we proxy bytes.
    import httpx
    auth = (os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])
    url = f"https://api.twilio.com/2010-04-01/Accounts/{auth[0]}/Recordings/{rec.sid}.mp3"
    r = httpx.get(url, auth=auth, follow_redirects=True, timeout=60.0)
    from fastapi.responses import Response
    return Response(content=r.content, media_type="audio/mpeg")


@app.get("/api/dashboard")
async def api_dashboard():
    total = len(call_meta)
    active = sum(1 for m in call_meta.values() if m.get("status") == "in-progress")
    completed = sum(1 for m in call_meta.values() if m.get("status") == "completed")
    durations = [m.get("duration") or 0 for m in call_meta.values() if m.get("duration")]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0
    return {
        "total_calls": total,
        "active_calls": active,
        "completed_calls": completed,
        "avg_duration_s": avg_duration,
        "active_call_sid": active_call_sid,
        "campaigns_count": len(campaigns),
    }


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------

class CampaignCreateRequest(BaseModel):
    name: str
    numbers: list[str]


CAMPAIGN_CALL_GAP_S = 8  # space outbound calls so we don't slam the carrier


async def _run_campaign(campaign_id: str):
    """Place calls sequentially with a gap between each."""
    camp = campaigns.get(campaign_id)
    if not camp:
        return
    camp["status"] = "running"
    _save_state_sync()
    for i, number in enumerate(camp["numbers"][camp["cursor"]:], start=camp["cursor"]):
        if camp.get("status") == "paused":
            _save_state_sync()
            return
        try:
            result = _place_call(number, campaign_id=campaign_id)
            camp["calls"].append({"to": number, "sid": result["sid"], "status": result["status"]})
        except Exception as e:
            camp["calls"].append({"to": number, "sid": None, "status": f"error: {e}"})
        camp["cursor"] = i + 1
        _save_state_sync()
        # Don't sleep after the last call.
        if camp["cursor"] < len(camp["numbers"]):
            await asyncio.sleep(CAMPAIGN_CALL_GAP_S)
    camp["status"] = "completed"
    _save_state_sync()


@app.post("/api/campaigns")
async def api_campaign_create(req: CampaignCreateRequest, background: BackgroundTasks):
    numbers = [n.strip() for n in req.numbers if n.strip().startswith("+")]
    if not numbers:
        raise HTTPException(400, "no valid E.164 numbers (must start with '+')")
    cid = f"camp_{int(time.time())}_{uuid.uuid4().hex[:6]}"
    campaigns[cid] = {
        "id": cid,
        "name": req.name or f"Campaign {cid[-6:]}",
        "created": time.time(),
        "numbers": numbers,
        "calls": [],
        "status": "queued",
        "cursor": 0,
    }
    background.add_task(_run_campaign, cid)
    return campaigns[cid]


@app.post("/api/campaigns/upload")
async def api_campaign_upload(file: UploadFile = File(...), name: str = "CSV Upload"):
    """Accept a CSV; numbers can be in a 'phone' column or the first column."""
    raw = (await file.read()).decode("utf-8", errors="replace")
    numbers: list[str] = []
    reader = csv.reader(io.StringIO(raw))
    rows = list(reader)
    if not rows:
        raise HTTPException(400, "CSV is empty")

    # Detect header
    header = rows[0]
    has_header = any(h.lower() in ("phone", "number", "to", "phone_number") for h in header)
    phone_idx = 0
    if has_header:
        for i, h in enumerate(header):
            if h.lower() in ("phone", "number", "to", "phone_number"):
                phone_idx = i
                break
        data_rows = rows[1:]
    else:
        data_rows = rows

    for r in data_rows:
        if not r or len(r) <= phone_idx:
            continue
        n = r[phone_idx].strip()
        if n and n.startswith("+"):
            numbers.append(n)
        elif n and n.isdigit() and len(n) == 10:
            # Assume Indian mobile if 10 digits with no '+'
            numbers.append("+91" + n)

    return {"numbers": numbers, "count": len(numbers), "name": name}


@app.get("/api/campaigns")
async def api_campaigns_list():
    out = sorted(campaigns.values(), key=lambda c: c.get("created", 0), reverse=True)
    return {"campaigns": out}


@app.get("/api/campaigns/{cid}")
async def api_campaign_detail(cid: str):
    if cid not in campaigns:
        raise HTTPException(404, "campaign not found")
    camp = campaigns[cid]
    # Enrich each call with current meta
    enriched_calls = []
    for c in camp["calls"]:
        meta = call_meta.get(c["sid"], {}) if c["sid"] else {}
        enriched_calls.append({**c, "meta": meta})
    return {**camp, "calls": enriched_calls}


@app.post("/api/campaigns/{cid}/pause")
async def api_campaign_pause(cid: str):
    if cid not in campaigns:
        raise HTTPException(404, "campaign not found")
    campaigns[cid]["status"] = "paused"
    return campaigns[cid]


@app.post("/api/campaigns/{cid}/resume")
async def api_campaign_resume(cid: str, background: BackgroundTasks):
    if cid not in campaigns:
        raise HTTPException(404, "campaign not found")
    if campaigns[cid]["status"] != "paused":
        return campaigns[cid]
    background.add_task(_run_campaign, cid)
    return campaigns[cid]


# Load any previously-saved state at module import (one-shot on startup).
_load_state()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), log_level="info")
