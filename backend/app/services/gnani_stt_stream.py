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
from starlette.websockets import WebSocketState
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

                # Two-way streaming state & coordination
                audio_buffer = bytearray()
                seen_finals = []
                latest_interim_text = ""
                last_interim_sent = ""
                stop_event = asyncio.Event()
                client_finished_speaking = asyncio.Event()
                frames_sent = 0
                bytes_received = 0

                async def pump_client_to_gnani():
                    nonlocal audio_buffer, frames_sent, bytes_received
                    try:
                        while not stop_event.is_set():
                            try:
                                message = await client_ws.receive()
                            except (WebSocketDisconnect, RuntimeError):
                                logger.info(f"[{session_id}] Client WebSocket disconnected while reading audio.")
                                stop_event.set()
                                break

                            msg_type = message.get("type", "")
                            if msg_type == "websocket.disconnect":
                                logger.info(f"[{session_id}] Client disconnected cleanly (code: {message.get('code', 1000)}).")
                                stop_event.set()
                                break

                            if "bytes" in message and message["bytes"]:
                                chunk = message["bytes"]
                                bytes_received += len(chunk)
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
                                        logger.info(
                                            f"[{session_id}] Client finished speaking: {frames_sent} frames sent ({bytes_received} bytes). Flushing VAD silence."
                                        )
                                        # Flush any remaining audio frame
                                        while len(audio_buffer) >= 1024:
                                            frame = bytes(audio_buffer[:1024])
                                            del audio_buffer[:1024]
                                            await gnani_ws.send(frame)
                                        if len(audio_buffer) > 0:
                                            pad = b"\x00" * (1024 - len(audio_buffer))
                                            await gnani_ws.send(bytes(audio_buffer) + pad)
                                            audio_buffer.clear()

                                        # Send 16 frames (~512ms) of silence to trigger Gnani server VAD reliably
                                        silence_frame = b"\x00" * 1024
                                        for _ in range(16):
                                            if stop_event.is_set():
                                                break
                                            await gnani_ws.send(silence_frame)

                                        client_finished_speaking.set()
                                        # Keep waiting for events or explicit client cancel/disconnect
                                        continue
                                    elif action == "cancel":
                                        logger.info(f"[{session_id}] Client explicitly cancelled STT recording.")
                                        stop_event.set()
                                        break
                                except json.JSONDecodeError:
                                    pass
                    except WebSocketDisconnect:
                        stop_event.set()
                    except asyncio.CancelledError:
                        pass
                    except Exception as exc:
                        logger.warning(f"[{session_id}] Client audio pump terminated: {config.redact_sensitive(str(exc))}")
                        stop_event.set()

                async def pump_gnani_to_client():
                    nonlocal latest_interim_text, last_interim_sent
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
                                logger.info(f"[{session_id}] Upstream GNANI Prisma ready.")
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
                                transcript_text = event.get("text", "").strip()
                                detected_lang = event.get("detected_language_code") or event.get("language") or "hi-IN"
                                is_final = bool(event.get("is_final", True))
                                duration_ms = float(event.get("audio_duration_ms", 0.0))

                                if is_final:
                                    if transcript_text in seen_finals:
                                        continue
                                    seen_finals.append(transcript_text)
                                    combined_finals = " ".join(seen_finals)
                                    authoritative_text = combined_finals if len(combined_finals) >= len(transcript_text) else transcript_text

                                    # If interim was more complete than final segment (e.g. final is only the trailing word), preserve interim
                                    if len(latest_interim_text) > len(authoritative_text) and (
                                        authoritative_text in latest_interim_text or len(authoritative_text.split()) == 1
                                    ):
                                        authoritative_text = latest_interim_text

                                    logger.info(f"[{session_id}] Emitting final transcript ({len(authoritative_text)} chars).")
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
                                    await asyncio.sleep(0.10)
                                    stop_event.set()
                                    break
                            elif event_type == "error":
                                err_code = event.get("code", 500)
                                err_msg = event.get("message", "Upstream transcription error")
                                sanitized = config.redact_sensitive(str(err_msg))
                                logger.error(f"[{session_id}] Upstream GNANI STT error ({err_code}): {sanitized}")
                                await client_ws.send_json({
                                    "type": "error",
                                    "code": err_code,
                                    "message": f"Gnani STT: {sanitized}",
                                    "fallback_available": True,
                                    "session_id": session_id,
                                })
                    except websockets.exceptions.ConnectionClosed as cc:
                        logger.info(f"[{session_id}] Upstream GNANI WebSocket closed ({cc.code}): {cc.reason}")
                    except asyncio.CancelledError:
                        pass
                    except Exception as exc:
                        sanitized = config.redact_sensitive(str(exc))
                        logger.warning(f"[{session_id}] Gnani event pump error: {sanitized}")
                    finally:
                        if not stop_event.is_set() and not client_finished_speaking.is_set():
                            try:
                                await client_ws.send_json({
                                    "type": "error",
                                    "code": 503,
                                    "message": "GNANI STT connection dropped unexpectedly.",
                                    "fallback_available": True,
                                    "session_id": session_id,
                                })
                            except Exception:
                                pass
                        stop_event.set()

                pump_task = asyncio.create_task(pump_client_to_gnani())
                event_task = asyncio.create_task(pump_gnani_to_client())

                # Wait for whichever finishes first (client stops/disconnects, or upstream GNANI disconnects)
                done, pending = await asyncio.wait(
                    [pump_task, event_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if client_finished_speaking.is_set() and not stop_event.is_set():
                    # If client pump finished normally (user clicked Done Speaking),
                    # allow event_task up to 5.0 seconds to receive the final transcript from Gnani!
                    if not event_task.done():
                        try:
                            await asyncio.wait_for(asyncio.shield(event_task), timeout=5.0)
                        except asyncio.TimeoutError:
                            logger.info(f"[{session_id}] STT session reached post-speech timeout waiting for final transcript.")
                        except Exception:
                            pass

                # Fallback: if user finished speaking and no final event was emitted, but an interim transcript was captured,
                # emit the interim text as final transcript to guarantee user input is not lost
                if client_finished_speaking.is_set() and not seen_finals and latest_interim_text:
                    logger.info(f"[{session_id}] Emitting latest interim text as final transcript fallback.")
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
                for t in (pump_task, event_task):
                    if not t.done():
                        t.cancel()
                        try:
                            await t
                        except (asyncio.CancelledError, Exception):
                            pass

        except websockets.exceptions.InvalidStatusCode as isc:
            status_code = getattr(isc, "status_code", 500)
            err_msg = f"Gnani WebSocket handshake rejected (HTTP {status_code})."
            if status_code in (401, 403):
                err_msg = "Gnani STT authentication failed. Check GNANI_API_KEY."
            elif status_code == 429:
                err_msg = "Gnani STT rate limit exceeded (HTTP 429)."
            logger.error(f"[{session_id}] {err_msg}")
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
            logger.error(f"[{session_id}] Gnani STT streaming session error: {sanitized}")
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
                if hasattr(client_ws, "client_state") and client_ws.client_state != WebSocketState.DISCONNECTED:
                    await client_ws.close()
            except Exception:
                pass


# Global singleton instance
gnani_stt_stream_handler = GnaniSTTStreamHandler()
