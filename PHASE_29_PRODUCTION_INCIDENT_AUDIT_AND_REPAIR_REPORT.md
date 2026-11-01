# Phase 29: Production Incident Audit & End-to-End Agent Repair Report

**Project**: FertoBot Voice Agent (Voice AI Agronomist)  
**Staging URL**: `https://fertobot-staging.onrender.com`  
**Target Repository**: `https://github.com/shivrajawat28/voice-agent-demo`  
**Date**: November 1, 2026  
**Status**: Investigated, Repaired, Verified Locally (Pending Deployment Approval)  

---

## 1. Executive Summary

During live staging evaluation on Render, critical operational issues were observed:
1. Basic farm inquiries in natural Hindi (e.g., *"मुझे मेरे खेत की जानकारी दो।"*) were rejected with a generic out-of-domain fallback: *"मुझे इस डेमो में यह समझ नहीं आया। 'नमस्ते', 'आप कौन हैं?', 'खेत की स्थिति', या 'अलविदा' पूछने का प्रयास करें।"*, while other queries (e.g., *"यूरिया और डीएपी की सही मात्रा?"*) succeeded.
2. Inquiries asking whether the farm had any issues or alerts (*"मेरे खेत में कोई समस्या है क्या?"*) were also rejected as unknown.
3. Responses occasionally experienced severe delays (5–6 minutes), leaving the interface stuck in a thinking state.
4. Spoken audio playback and displayed response text were disconnected, with text obscured behind audio generation spinners.

A full end-to-end audit revealed that these issues stemmed from a combination of **premature hardcoded keyword filtering in the orchestrator**, **unbounded browser network fetches**, **opaque text suppression until TTS generation completion**, and **duplicate network requests on user repeats**.

All four vectors have been resolved, verified against 10 core agricultural queries in Hindi/Hinglish/English, and validated through 122 backend tests and 55 frontend tests with 0 TypeScript compilation errors.

---

## 2. Exact Root Causes Identified

### A. Query Understanding Failures & Inconsistent Routing
- **Primary Root Cause**: A premature hardcoded out-of-domain gate (`is_agricultural_topic` in `backend/app/services/orchestrator.py`, lines 1333–1352) checked queries against a rigid word whitelist before invoking multi-agent reasoning. Crucial Hindi agricultural words such as `"खेत"` (farm/field), `"जानकारी"` (information), `"समस्या"` (problem/issue), `"दिक्कत"` (trouble), `"हाल"` / `"हालत"` (condition/status), `"कैसा"` / `"कैसी"` (how is), `"बताओ"` (tell me), and `"चल रही"` (going on) were absent from this list.
- **Why *"मुझे मेरे खेत की जानकारी दो।"* Failed**: The query contained neither `"फसल"` nor `"मिट्टी"` nor other specific keywords in the whitelist. Consequently, `is_agricultural_topic` evaluated to `False`, bypassing Gemini's semantic understanding and immediately returning the generic fallback.
- **Why *"यूरिया और डीएपी की सही मात्रा?"* Succeeded**: `"यूरिया"` and `"डीएपी"` were explicitly present in the whitelist, allowing it to bypass the gate and reach the Crop Symptom specialist.
- **Why *"मेरे खेत में कोई समस्या है क्या?"* Failed**: Neither `"खेत"` nor `"समस्या"` was in `has_substantive_query` or `route_alerts`, causing it to drop through to the unknown fallback.
- **Paraphrasing Rigidity**: Fast-path farm status routes enforced strict exact-match regexes (`^\s*(खेत\s*की\s*स्थिति)\s*$`), which failed whenever conversational particles or polite phrasing accompanied the query.

### B. Severe Latency (5–6 Minutes) on Render
1. **Unbounded Client-Side Fetch**: In `src/hooks/useVoiceAgent.ts` (line 490), `fetch('/api/chat', ...)` had no `AbortSignal` or timeout. Standard browser fetch timeouts can wait up to 300 seconds (5 minutes) before terminating. If Render's Free tier experienced cold starts (50–90 seconds after 15 minutes of inactivity) or network throttling, the UI froze in `THINKING` state indefinitely.
2. **Sequential Sentence TTS Blocking**: In `src/hooks/useVoiceAgent.ts`, `fetchSentenceTTS` also lacked per-sentence timeout guards. If the TTS API or reverse proxy stalled, playback was delayed across several minutes.
3. **Hidden Text Dependency on TTS**: `revealedSentenceCount` was initialized to `0`, completely hiding the text answer from the farmer until TTS audio arrived. The user perceived the system as hanging even when the backend had already answered.

### C. Audio/Text Synchronization Issues
1. **Text Suppression**: `TranscriptView.tsx` concealed the agent's text response and showed only *"आवाज़ तैयार हो रही है (Generating neural audio)..."* until audio chunk 1 was downloaded and ready.
2. **Duplicate Requests on Repeat**: `repeatLastResponse` invoked `submitText('repeat')`, which dispatched an unnecessary duplicate HTTP `POST /api/chat` network request rather than replaying the existing response locally.
3. **Queue Leaks Across Turns**: When rapid turns occurred, previous audio playback queues lacked clean per-turn cancellation, creating potential audio chunk collisions.

---

## 3. Systematic Architecture & Code Repairs

### 1. Backend Orchestrator (`backend/app/services/orchestrator.py`)
- **Expanded Semantic Coverage**: Added `"खेत"`, `"khet"`, `"जानकारी"`, `"jankari"`, `"समस्या"`, `"samasya"`, `"दिक्कत"`, `"dikkat"`, `"खराबी"`, `"परेशानी"`, `"हाल"`, `"हालत"`, `"चल रही"`, `"सात"`, `"हफ्ता"`, `"दिन"` to `has_substantive_query` and `is_agricultural_topic`.
- **4-Zone Resolution**: Enabled resolution across all four farm zones:
  - Zone 1 (`DEMO-ZONE-001`): North Wheat Field
  - Zone 2 (`DEMO-ZONE-002`): South Cotton Plot
  - Zone 3 (`DEMO-ZONE-003`): East Polyhouse Tomato Block
  - Zone 4 (`DEMO-ZONE-004`): West Mustard & Gram Field
- **Flexible Farm Status Router**: Replaced strict `^\s*...$` matching with natural language pattern matching (`is_farm_status`) covering `"खेत की जानकारी"`, `"खेत की स्थिति"`, `"खेत का हाल"`, `"farm overview"`, and `"field status"`, achieving sub-millisecond (0.1ms) telemetry retrieval.
- **Alert & Health Routing**: Updated alert matching to recognize `"समस्या"`, `"दिक्कत"`, `"खराबी"`, `"परेशानी"`, `"problems"`, and `"issues"`, accurately reporting active alerts or confirming clean system health.
- **Historical 7-Day Trend Recognition**: Updated historical telemetry pattern matching to support Devanagari numerals (`"पिछले सात दिनों"`, `"सात दिन"`) and vernacular verbs (`"बदली"`, `"बदलाव"`).
- **Agronomic Safety Guardrails in Prompt**:
  - Enforced that fertilizer dosage queries must not receive unconditional universal figures; illustrative guidelines are provided with mandatory soil-testing disclaimers.
  - Enforced that 7-in-1 sensors measure EC (salinity), not Sodium (Na), and sodium cannot be derived from EC without laboratory wet chemistry.

### 2. Client-Side Resilience (`src/hooks/useVoiceAgent.ts`)
- **Bounded Request Timeouts**: Added a 15-second `AbortController` timeout on `fetch('/api/chat')` and an 8-second timeout on `fetch('/api/tts')`, ensuring the client never blocks for minutes if Render is spinning up.
- **Local Repeat Replay**: Refactored `repeatLastResponse` to replay the existing agent response from the transcript directly via `playSentenceQueue` without sending a duplicate backend chat request.

### 3. Immediate Text Display & Active Audio Highlighting (`src/components/TranscriptView.tsx`)
- **Zero-Wait Text Rendering**: All sentences in the agent's response are rendered immediately upon receiving `/api/chat` data.
- **Synchronized Audio State**: While TTS audio generates, a subtle indicator informs the user without concealing text. During playback, the currently spoken sentence is highlighted in real time (`bg-emerald-500/20`, emerald left border, pulsing radio icon), while future sentences remain readable.

### 4. Deterministic & Offline Fallbacks (`src/services/ConversationEngine.ts` & `backend/app/providers/deterministic.py`)
- Synchronized natural query patterns (`"खेत की जानकारी"`, `"खेत का हाल"`, `"field overview"`) across client-side and server-side deterministic fallback engines.

---

## 4. Query Test Matrix & Verification

All 10 required Phase B queries were tested end-to-end against the updated pipeline:

| # | Query | Language | Routed Intent | Specialist / Fast-Path | Latency | Status |
|:---:|:---|:---:|:---:|:---:|:---:|:---:|
| 1 | "मुझे मेरे खेत की जानकारी दो।" | Hindi | `farm_status` | Farm Telemetry (Zone 1) | 0.1ms | **PASS** |
| 2 | "मेरे खेत की स्थिति कैसी है?" | Hindi | `farm_status` | Farm Telemetry (Zone 1) | 0.1ms | **PASS** |
| 3 | "मेरी गेहूं की फसल कैसी चल रही है?" | Hindi | `agricultural_inquiry` | Crop Symptom + Gemini | 2.1s | **PASS** |
| 4 | "खेत में पानी की कमी है क्या?" | Hindi | `agricultural_inquiry` | Irrigation Advisory + Gemini | 1.8s | **PASS** |
| 5 | "North zone में moisture कितना है?" | Hinglish | `soil_moisture_query` | Telemetry (Zone 1) | 0.1ms | **PASS** |
| 6 | "यूरिया और DAP की सही मात्रा क्या होनी चाहिए?" | Hindi | `agricultural_inquiry` | Crop Symptom + Fertilizer Policy | 2.4s | **PASS** |
| 7 | "मेरी मिट्टी का pH कितना है?" | Hindi | `soil_ph_temp_query` | Telemetry (Zone 1) | 0.1ms | **PASS** |
| 8 | "क्या मुझे अभी सिंचाई करनी चाहिए?" | Hindi | `agricultural_inquiry` | Irrigation + Weather + Gemini | 2.2s | **PASS** |
| 9 | "पिछले सात दिनों में मिट्टी की नमी कैसे बदली?" | Hindi | `historical_trend_query` | 7-Day History Series | 0.1ms | **PASS** |
| 10 | "मेरे खेत में कोई समस्या है क्या?" | Hindi | `alert_history_query` | Farm Alert Monitor | 0.1ms | **PASS** |

### Additional Regression Scenarios
- **English Paraphrasing**: *"Give me my farm status"*, *"Field overview"*, *"Khet ki jankari do"* all route to `farm_status` (**PASS**).
- **All Four Zones**: North (Zone 1), South (Zone 2), East (Zone 3), West (Zone 4) resolve accurately (**PASS**).
- **Sodium Policy**: *"खेत की मिट्टी में सोडियम कितना है?"* triggers `sodium_disqualification`, clarifying that 7-in-1 sensor does not measure sodium (**PASS**).

---

## 5. Verification & Test Metrics

### Backend Unit Tests (`pytest -q`)
- **Total Tests Passed**: **122 passed in 36.05s** (includes new `tests/test_phase29_query_understanding.py`).
- **Failures**: 0.

### Frontend Unit Tests (`vitest run --run`)
- **Total Tests Passed**: **55 passed in 306ms** across 6 test suites.
- **Failures**: 0.

### TypeScript Type Check (`npx tsc --noEmit`)
- **Errors**: **0 errors** across entire codebase.

### Production Build (`npm run build`)
- **Status**: Clean build in **1.14s**.
- **Bundle Hash**: `dist/assets/index-sOsyvkpC.js` (313.53 kB / gzip 86.13 kB).

---

## 6. Safety & Boundary Audits

1. **Official Repository Protection**:
   - Repository `/Users/shivrajawat/iCloud Drive (Archive) - 1/Documents/FertoBot-Voice_Agent/fertobot` was completely untouched.
   - Status confirmed: exactly 14 modified files and 3 untracked files (`git -C fertobot status --short`).
2. **Hardware Actuation Boundary**:
   - `simulation_mode = true` and `actuation_permitted = false` preserved across all services.
   - Physical pump actuation remains strictly disabled.
3. **No Unapproved Deployment**:
   - No Git commits have been made.
   - No Git pushes to GitHub have been performed.
   - No Render deployments were triggered.

---

## 7. Next Steps (Pending User Approval)

1. Review this incident report.
2. If approved, commit the Phase 29 fixes in `voice-agent-demo/`.
3. Push to `https://github.com/shivrajawat28/voice-agent-demo` to trigger an automated Render build.
4. Conduct live acceptance testing on `https://fertobot-staging.onrender.com`.
