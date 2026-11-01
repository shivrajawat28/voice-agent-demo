# Phase 26: Voice Pipeline Reliability, Synchronization & Latency Optimization Audit

**Project:** FertoBot AI Agronomist & Voice Agent  
**Working Repository:** `voice-agent-demo/`  
**Production Staging Target:** `https://fertobot-staging.onrender.com`  
**Current Baseline Commit:** `283da0ec96a078649724318504a66655522b13d9`  
**Date:** November 1, 2026  
**Document:** `PHASE_26_VOICE_AUDIT.md`

---

## 1. Executive Summary & Audit Scope

This audit provides a rigorous, end-to-end diagnosis of the voice interaction pipeline across browser audio capture, streaming Speech-to-Text (GNANI Prisma v3.0 / Browser Web Speech API), conversational turn synchronization, and Text-to-Speech playback (GNANI Timbre v2.5 / Web Audio Queue).

Every reported symptom has been traced to concrete code paths and race conditions in the current implementation.

---

## 2. Relevant Source Files Audited

### Frontend
- `src/services/VoiceController.ts`: AudioContext capture, 16 kHz PCM resampling, WebSocket streaming, SpeechRecognition fallback, and audio playback.
- `src/services/AgentStateMachine.ts`: Finite state machine governing interaction lifecycle (`idle`, `listening`, `processing`, `speaking`, `error`).
- `src/hooks/useVoiceAgent.ts`: Voice session orchestrator, sentence queue playback, Done Speaking handler, and state machine listener.
- `src/components/VoiceAssistantView.tsx`: User interface for microphone trigger, Done Speaking button, live VU meter, and waveform.
- `src/components/VoiceVisualizer.tsx`: Visualizer canvas, silence detection timer, and device configuration.
- `src/types/voiceAgent.ts`: Type contracts for states, events, payloads, and messages.

### Backend
- `backend/app/services/gnani_stt_stream.py`: Upstream WebSocket proxy to GNANI Prisma v3.0 (`wss://api.vachana.ai/stt/v3/stream`).
- `backend/app/providers/gnani_tts.py`: GNANI Vachana REST TTS client (`https://api.vachana.ai/api/v1/tts/inference`).
- `backend/app/services/orchestrator.py`: Multi-agent orchestration, sentence boundary partitioning (`split_into_sentences`), and Hindi normalization.
- `backend/app/main.py`: Fast-API endpoints (`/api/ws/stt`, `/api/chat`, `/api/tts`).

---

## 3. End-to-End Pipeline Request Trace

```
[User speaks: "मेरे खेत की स्थिति क्या है?"]
               │
               ▼
1. Browser MediaStream: 48 kHz float audio captured via ScriptProcessorNode / AudioContext
               │
               ▼
2. VoiceController.resampleAudio(): Linear interpolation 48 kHz -> 16 kHz
               │
               ▼
3. VoiceController.floatTo16BitPCM(): 16-bit Little-Endian PCM frames (512 samples / 1024 bytes)
               │
               ▼ (WebSocket client -> backend proxy: /api/ws/stt)
4. GnaniSTTStreamHandler: Buffers and forwards 1024-byte frames to wss://api.vachana.ai/stt/v3/stream
               │
               ▼ (GNANI Prisma v3.0 server events)
5. Intermediate Events: {"type": "transcript", "text": "...", "is_final": false}
               │
6. Client clicks "Done Speaking": Sends {"action": "stop"} -> Server sends 8 silence frames (256ms)
               │
7. GNANI Final Event: {"type": "transcript", "text": "...", "is_final": true}
               │
               ▼
8. handleProcessInput(): Chat request POST /api/chat with session_id & active_zone_id
               │
               ▼
9. Gemini / Orchestrator: Multi-agent synthesis -> response reply + sentences array
               │
               ▼
10. playSentenceQueue(): Sequential TTS fetch and audio playback
               │
               ▼
11. Browser Audio: Decodes WAV bytes and plays via HTMLAudioElement / Web Audio API
```

---

## 4. Root Cause Analysis of Reported Issues

### Issue A: Speech recognition loses or delays user input
**Observed Symptoms:**
1. Agent captures only the last word (e.g., "स्थिति" instead of "मेरे खेत की स्थिति क्या है?").
2. Speech is not recognized at all; interaction is dropped.
3. Input processed only on the subsequent microphone click.
4. Consecutive requests occasionally contain both previous and current utterances.

**Root Causes Verified in Code:**
1. **Flawed Segment Reassembly in Backend Proxy (`backend/app/services/gnani_stt_stream.py:205-209`):**
   ```python
   seen_finals = set()
   ...
   if is_final:
       seen_finals.add(transcript_text)
       combined_finals = " ".join(sorted(seen_finals, key=lambda x: list(seen_finals).index(x)))
   ```
   - `seen_finals` was a Python `set()`. Doing `list(seen_finals).index(x)` produces arbitrary hash-bucket ordering, reordering words unpredictably.
   - More critically: When GNANI streams in real time, interim hypotheses contain the full running text with `is_final: false`. When the user clicks "Done Speaking", the tail silence frame may cause GNANI to emit an end-of-speech segment containing **only the final trailing token** (e.g. `text: "स्थिति", is_final: true`).
   - Because previous text arrived as `is_final: false`, `seen_finals` contains **only** the last token! All preceding words ("मेरे खेत की") were discarded.
2. **Premature Finalization on Intermediate Segments (`src/services/VoiceController.ts:549-555`):**
   - In streaming mode, GNANI emits `is_final: true` on intermediate pauses/clauses while the user is still speaking.
   - `VoiceController` immediately invoked `this.callbacks.onTranscriptionResult(data.text)` on *every* `is_final: true` event.
   - In `useVoiceAgent.ts:526-529`, this immediately transitioned the state machine to `processing` and dispatched a chat query for the half-finished sentence! When the user finished speaking the remainder, the state machine was busy or the subsequent text was orphaned until the next microphone click.
3. **Absence of Utterance/Session Scoping in Frontend (`src/services/VoiceController.ts` & `src/hooks/useVoiceAgent.ts`):**
   - Transcripts lacked an explicit `utteranceId` and `sessionId`. Late-arriving WebSocket messages or lingering recognition events from a previous turn leaked into the next turn buffer because there was no generation check.
4. **Browser Recognition Auto-Termination Bug (`src/services/VoiceController.ts:390`):**
   - `recognition.continuous = false;` caused Chrome and Safari to abort microphone capture on any natural pause (> 1 second).

---

### Issue B: Delayed and Fragmented Agent Responses
**Observed Symptoms:**
1. Noticeable latency before first audible response.
2. Short greeting spoken (e.g. "नमस्ते किसान भाई।"), followed by a 1–2 second awkward pause, and then the main response resumes.
3. User assumes the agent has finished speaking and interrupts.

**Root Causes Verified in Code:**
1. **Micro-Chunk Partitioning and TTS Queue Starvation (`backend/app/services/orchestrator.py:54` & `src/hooks/useVoiceAgent.ts:297`):**
   - `split_into_sentences()` partitioned text on every Hindi danda (`।`).
   - A short greeting ("नमस्ते किसान भाई।") is only 3 words (~1.0 second of audio).
   - Sentence 0 was fetched and started playing immediately. While Sentence 0 played, the prefetch for Sentence 1 was triggered.
   - However, Sentence 1 is a detailed agricultural response (30+ words). GNANI TTS synthesis over WAN for a 30-word sentence requires ~1.2 to 1.8 seconds.
   - Sentence 0 finished playing in 1.0 second. The queue ran out of audio, creating a dead silence of 500–1000ms before Sentence 1 audio arrived.
2. **Global Request Lock in TTS Provider (`backend/app/providers/gnani_tts.py:99, 243`):**
   ```python
   self._request_lock = asyncio.Lock()
   ...
   async with self._request_lock:
   ```
   - An `asyncio.Lock()` wrapped the entire HTTP request in `GnaniTTSProvider.synthesize()`.
   - Even though the frontend attempted to prefetch Sentence 1 while Sentence 0 was in flight, the backend completely serialized the requests! Concurrent synthesis was impossible.
3. **Per-Request HTTP Client Destruction (`backend/app/providers/gnani_tts.py:254, 264`):**
   - An `httpx.AsyncClient` was instantiated and closed (`await client.aclose()`) on *every single sentence request*.
   - This forced a brand new TCP handshake and TLS negotiation (250–400ms overhead) to `https://api.vachana.ai` on every sentence.
4. **Audio Element Construction Delay in Browser (`src/services/VoiceController.ts:887`):**
   - `new Audio(url)` was instantiated inside the promise callback only after `audio.onended` resolved, incurring browser media decoder startup latency between segments.

---

### Issue C: Microphone and Done Speaking Button Unreliability
**Observed Symptoms:**
1. Clicking "Done Speaking" sometimes does nothing.
2. Microphone stops automatically while the user is still speaking.
3. Session remains stuck in `listening` or `processing`.

**Root Causes Verified in Code:**
1. **Missing `finalizing` State in `AgentStateMachine.ts`:**
   - When the user clicked "Done Speaking", the agent remained in state `'listening'`.
   - The UI gave zero visual confirmation of finalization. Users clicked "Done Speaking" repeatedly, causing race conditions.
2. **Silent Failure on Missing STT Final Event (`src/services/VoiceController.ts:702-706`):**
   - When "Done Speaking" was clicked, `stopGnaniStreaming()` sent `{"action": "stop"}` and started a 6-second timer.
   - If GNANI did not emit a distinct `final_transcript` event (because it had already emitted the full text as an interim hypothesis), the 6-second timer simply closed the socket and called `sm.cancel()`.
   - **The accumulated interim transcript was thrown away without submission!**
3. **No Idempotency Guards on Button Submissions:**
   - Multiple clicks on "Done Speaking" or concurrent speech events were not gated by an active `isFinalizing` lock.

---

## 5. Proposed Architectural Fixes

```
+---------------------------------------------------------------------------------------+
|                               PHASE 26 FIX MATRIX                                     |
+---------------------------------------------------------------------------------------+
| 1. STT Session Manager       | Unique sessionId + utteranceId on every mic session    |
| 2. Reconciled Finalizer      | Uses authoritative final OR fallback to full interim   |
| 3. State Machine Upgrade     | Explicit 'finalizing' state with UI feedback           |
| 4. Continuous Mic Capture    | continuous: true for Web Speech; no early cutoff       |
| 5. Intelligent Chunking      | Merge short greetings (< 6 words) into first sentence  |
| 6. TTS Concurrency & Pool    | Remove backend request lock; reuse keep-alive HTTP client|
| 7. Gapless Audio Chaining    | Pre-decode & preload audio buffers for seamless queue   |
| 8. Turn Idempotency Guard    | Exactly one chat request per utterance                 |
+---------------------------------------------------------------------------------------+
```

---

## 6. Risk Assessment & Regression Tests

| Risk | Mitigation | Test Strategy |
| :--- | :--- | :--- |
| **STT text duplication** | Authoritative utterance buffer replaces rather than appends provisional text | Unit test with multiple interim updates followed by final |
| **Premature submission** | Only submit when `Done Speaking` is clicked or clear finalization occurs | Test speech with natural 2-second pauses |
| **Audio queue overlap** | Strict sequential audio chaining via Web Audio / AudioQueue controller | Test queueing 3 rapid audio chunks |
| **Memory leak from keep-alive** | Use singleton managed `httpx.AsyncClient` with standard connection pooling | Load test with 50 sequential syntheses |

---

*Audit Complete. Proceeding immediately to Phase 26 Implementation.*
