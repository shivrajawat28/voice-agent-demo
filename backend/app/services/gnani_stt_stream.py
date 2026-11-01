"""
Gnani AI (Prisma v3.0) Real-Time Streaming Speech-to-Text WebSocket Service
Proxies browser microphone PCM audio to Gnani's WebSocket endpoint:
- Upstream: wss://api.vachana.ai/stt/v3/stream
- Model: prisma-v3.0
- Language: indic-auto (dynamic Hindi/English/Hinglish detection)
- Audio spec: 16-bit little-endian mono PCM, 512 samples/frame (1024 bytes/frame)
"""
import asyncio
import json
import logging
import uuid
from typing import Optional, Dict, Any, Callable
from fastapi import WebSocket, WebSocketDisconnect
import websockets
from app import config

logger = logging.getLogger(__name__)


class GnaniSTTStreamHandler:
    """
    Manages an authenticated streaming WebSocket session bridging
    browser audio to Gnani's Prisma v3.0 real-time STT engine.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        ws_url: Optional[str] = None,
        model: Optional[str] = None,
        language_code: Optional[str] = None,
        format_style: str = "transcribe",
        timeout_seconds: float = 30.0,
        ws_connect_override: Optional[Callable] = None,
    ):
        self.api_key = api_key if api_key is not None else config.GNANI_API_KEY
        self.ws_url = ws_url or config.GNANI_STT_WS_URL
        self.model = model or config.GNANI_STT_MODEL
        self.language_code = language_code or config.GNANI_STT_LANGUAGE_CODE
        self.format_style = format_style
        self.timeout_seconds = timeout_seconds
        self._ws_connect_override = ws_connect_override

    def is_configured(self) -> bool:
        """Returns True if a valid Gnani API key is configured."""
        return bool(self.api_key and len(self.api_key) > 5)

    def build_headers(self) -> Dict[str, str]:
        """Constructs Gnani STT WebSocket upgrade connection headers."""
        return {
            "X-API-Key-ID": self.api_key or "",
            "model": self.model,
            "language_code": self.language_code,
            "format": self.format_style,
        }

    async def handle_client_websocket(self, client_ws: WebSocket):
        """
        Main handler for client connection to /api/ws/stt.
        """
        await client_ws.accept()
        session_id = f"stt-{uuid.uuid4().hex[:8]}"

        # 1. Guard against missing credentials
        if not self.is_configured():
            logger.info("Gnani STT: missing API key, notifying client of credentials requirement.")
            await client_ws.send_json({
                "type": "error",
                "code": "AUTH_REQUIRED",
                "message": "Gnani STT unavailable — API credentials required.",
                "fallback_available": True,
                "session_id": session_id,
            })
            await asyncio.sleep(0.1)
            await client_ws.close(code=1008, reason="Gnani credentials required")
            return

        # 2. Notify client that upstream connection is initiating
        await client_ws.send_json({
            "type": "status",
            "status": "connecting",
            "message": f"Connecting to Gnani Prisma v3.0 ({self.model})...",
            "session_id": session_id,
        })

        headers = self.build_headers()
        connect_fn = self._ws_connect_override or websockets.connect

        try:
            async with connect_fn(
                self.ws_url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            ) as gnani_ws:
                await client_ws.send_json({
                    "type": "status",
                    "status": "connected",
                    "message": "Connected to Gnani Prisma v3.0 real-time STT.",
                    "session_id": session_id,
                    "model": self.model,
                    "language": self.language_code,
                })

                # Two-way streaming tasks
                audio_buffer = bytearray()
                seen_finals = []
                latest_interim_text = ""
                last_interim_sent = ""
                stop_event = asyncio.Event()
                client_finished_speaking = asyncio.Event()

                async def pump_client_to_gnani():
                    nonlocal audio_buffer
                    frames_sent = 0
                    try:
                        while not stop_event.is_set():
                            message = await client_ws.receive()
                            if "bytes" in message and message["bytes"]:
                                chunk = message["bytes"]
                                audio_buffer.extend(chunk)

                                # Forward in 512-sample (1024-byte) frames
                                while len(audio_buffer) >= 1024:
                                    frame = bytes(audio_buffer[:1024])
                                    del audio_buffer[:1024]
                                    await gnani_ws.send(frame)
                                    frames_sent += 1

                            elif "text" in message and message["text"]:
                                try:
                                    data = json.loads(message["text"])
                                    action = data.get("action")
                                    if action == "stop":
                                        logger.info(f"Client finished speaking after {frames_sent} frames. Flushing VAD silence.")
                                        # Flush any remaining audio frame
                                        while len(audio_buffer) >= 1024:
                                            frame = bytes(audio_buffer[:1024])
                                            del audio_buffer[:1024]
                                            await gnani_ws.send(frame)
                                        if len(audio_buffer) > 0:
                                            pad = b"\x00" * (1024 - len(audio_buffer))
                                            await gnani_ws.send(bytes(audio_buffer) + pad)
                                            audio_buffer.clear()

                                        # Send 8 frames (~256ms) of silence to trigger Gnani server VAD without artificial latency
                                        silence_frame = b"\x00" * 1024
                                        for _ in range(8):
                                            if stop_event.is_set():
                                                break
                                            await gnani_ws.send(silence_frame)

                                        client_finished_speaking.set()
                                        break
                                    elif action == "cancel":
                                        logger.info("Client explicitly cancelled STT recording.")
                                        stop_event.set()
                                        break
                                except json.JSONDecodeError:
                                    pass
                    except WebSocketDisconnect:
                        stop_event.set()
                    except asyncio.CancelledError:
                        pass
                    except Exception as exc:
                        logger.warning(f"Client audio pump terminated: {config.redact_sensitive(str(exc))}")
                        stop_event.set()

                async def pump_gnani_to_client():
                    try:
                        async for raw_msg in gnani_ws:
                            if stop_event.is_set():
                                break
                            try:
                                if isinstance(raw_msg, bytes):
                                    raw_text = raw_msg.decode("utf-8")
                                else:
                                    raw_text = str(raw_msg)
                                event = json.loads(raw_text)
                            except Exception:
                                continue

                            event_type = event.get("type", "")

                            if event_type == "connected":
                                await client_ws.send_json({
                                    "type": "gnani_ready",
                                    "session_id": session_id,
                                    "details": event,
                                })
                            elif event_type == "processing":
                                await client_ws.send_json({
                                    "type": "processing",
                                    "session_id": session_id,
                                })
                            elif event_type == "transcript":
                                nonlocal latest_interim_text, last_interim_sent
                                transcript_text = event.get("text", "").strip()
                                detected_lang = event.get("detected_language_code") or event.get("language") or "hi-IN"
                                is_final = bool(event.get("is_final", True))
                                duration_ms = float(event.get("audio_duration_ms", 0.0))

                                if is_final:
                                    if transcript_text in seen_finals:
                                        continue
                                    seen_finals.append(transcript_text)
                                    # If previous finals exist, combine them in strict arrival order
                                    combined_finals = " ".join(seen_finals)
                                    authoritative_text = combined_finals if len(combined_finals) >= len(transcript_text) else transcript_text

                                    # If interim was more complete than final segment (e.g. final is only the trailing word), preserve interim
                                    if len(latest_interim_text) > len(authoritative_text) and (
                                        authoritative_text in latest_interim_text or len(authoritative_text.split()) == 1
                                    ):
                                        authoritative_text = latest_interim_text

                                    await client_ws.send_json({
                                        "type": "final_transcript",
                                        "text": authoritative_text,
                                        "segment_text": transcript_text,
                                        "is_final": True,
                                        "detected_language": detected_lang,
                                        "duration_ms": duration_ms,
                                        "session_id": session_id,
                                        "provider": "gnani_prisma_v3",
                                    })
                                else:
                                    if transcript_text and transcript_text != last_interim_sent:
                                        latest_interim_text = transcript_text
                                        last_interim_sent = transcript_text
                                        await client_ws.send_json({
                                            "type": "transcript",
                                            "text": transcript_text,
                                            "is_final": False,
                                            "detected_language": detected_lang,
                                            "duration_ms": duration_ms,
                                            "session_id": session_id,
                                            "provider": "gnani_prisma_v3",
                                        })

                                if is_final and client_finished_speaking.is_set():
                                    # Low-latency 100ms grace window for immediately queued back-to-back frames
                                    await asyncio.sleep(0.10)
                                    stop_event.set()
                                    break
                            elif event_type == "error":
                                err_code = event.get("code", 500)
                                err_msg = event.get("message", "Upstream transcription error")
                                sanitized = config.redact_sensitive(str(err_msg))
                                await client_ws.send_json({
                                    "type": "error",
                                    "code": err_code,
                                    "message": f"Gnani STT: {sanitized}",
                                    "fallback_available": True,
                                    "session_id": session_id,
                                })
                    except asyncio.CancelledError:
                        pass
                    except Exception as exc:
                        sanitized = config.redact_sensitive(str(exc))
                        logger.warning(f"Gnani event pump error: {sanitized}")

                pump_task = asyncio.create_task(pump_client_to_gnani())
                event_task = asyncio.create_task(pump_gnani_to_client())

                # Wait for either client pump to finish or error/stop
                await pump_task

                if not stop_event.is_set():
                    # If client pump finished normally (user stopped speaking),
                    # allow event_task up to 2.5 seconds to receive the final transcript from Gnani!
                    try:
                        await asyncio.wait_for(event_task, timeout=2.5)
                    except asyncio.TimeoutError:
                        logger.info("STT session reached post-speech timeout waiting for final transcript.")

                # Fallback: if user finished speaking and no final event was emitted, but an interim transcript was captured,
                # emit the interim text as final transcript to guarantee user input is not lost
                if client_finished_speaking.is_set() and not seen_finals and latest_interim_text:
                    logger.info("Emitting latest interim text as final transcript fallback.")
                    try:
                        await client_ws.send_json({
                            "type": "final_transcript",
                            "text": latest_interim_text,
                            "segment_text": latest_interim_text,
                            "is_final": True,
                            "detected_language": "hi-IN",
                            "duration_ms": 0.0,
                            "session_id": session_id,
                            "provider": "gnani_prisma_v3",
                        })
                    except Exception:
                        pass

                stop_event.set()
                if not event_task.done():
                    event_task.cancel()
                    try:
                        await event_task
                    except asyncio.CancelledError:
                        pass

        except websockets.exceptions.InvalidStatusCode as isc:
            status_code = getattr(isc, "status_code", 500)
            err_msg = f"Gnani WebSocket handshake rejected (HTTP {status_code})."
            if status_code in (401, 403):
                err_msg = "Gnani STT authentication failed. Check GNANI_API_KEY."
            elif status_code == 429:
                err_msg = "Gnani STT rate limit exceeded (HTTP 429)."
            logger.error(err_msg)
            try:
                await client_ws.send_json({
                    "type": "error",
                    "code": status_code,
                    "message": err_msg,
                    "fallback_available": True,
                    "session_id": session_id,
                })
            except Exception:
                pass
        except Exception as exc:
            sanitized = config.redact_sensitive(str(exc))
            logger.error(f"Gnani STT streaming session error: {sanitized}")
            try:
                await client_ws.send_json({
                    "type": "error",
                    "code": 502,
                    "message": f"Failed to connect to Gnani STT stream: {sanitized}",
                    "fallback_available": True,
                    "session_id": session_id,
                })
            except Exception:
                pass
        finally:
            try:
                await client_ws.close()
            except Exception:
                pass


# Global singleton instance
gnani_stt_stream_handler = GnaniSTTStreamHandler()
