---
name: openai-realtime-quirks
description: >
  Hard-won OpenAI Realtime API behaviors for realtime voice sessions:
  VAD configuration (server_vad vs semantic_vad), false barge-in filtering, audio-stream continuity,
  reconnect/buffer handling, event name/shape gotchas, capability-field recovery, reasoning config,
  and per-response instruction overrides. Auto-loaded background knowledge when working on realtime
  voice sessions, VAD/turn-detection, barge-in, audio streaming, or OpenAI Realtime session config.
metadata:
  type: reference
---

# OpenAI Realtime API — Project Quirks

Background knowledge for WebSocket-based OpenAI Realtime voice sessions. Derived from production
incidents and post-task reviews. **Always verify session/event
field shapes against the SDK type source, never memory** (`openai/types/realtime/…`,
`openai/types/beta/realtime/…`) — see `ai-docs-lookup`.

## 1. Turn detection: prefer `server_vad` for structured conversations

- **`server_vad` + `silence_duration_ms`** is an energy-based exact timer — use it for structured
  conversations (e.g., interviews, coaching) where mid-sentence thinking pauses must NOT trigger
  turn-end. Default `silence_duration_ms=3000` (prevents interruption on 1–2 s pauses); tunable per
  feature via env.
- **`semantic_vad`** fires when a phrase *sounds* semantically complete, at **1–2.5 s regardless of
  `eagerness=low`** (the advertised ~4 s is not real). Only use it where early turn-taking is wanted.
- **Mutually exclusive params:** `eagerness` is INVALID for `server_vad`; `silence_duration_ms` is
  INVALID for `semantic_vad` (OpenAI returns an API error). The `configure_session()` conditional
  dict must add one and omit the other. `semantic_vad` exposes only `type`, `eagerness`
  (auto/low/medium/high), `create_response`, `interrupt_response` — no sensitivity/threshold knobs.
- On any **realtime model upgrade**, re-test turn-taking and session length — better
  instruction-following can surface latent prompt/VAD issues.

## 2. False barge-ins: filter on the backend, never gate frontend audio

Background noise / mic echo produces spurious `speech_started → speech_stopped` with a delayed
transcript that fires `_execute_confirmed_interrupt()` after speech already ended (log signature:
`speech_stopped (…ms, duration_ms=null) → barge_in_pending_delayed_transcript → sent_bytes=0`).

- **Two guards, always deployed together:** (1) a **duration filter** in `_handle_speech_stopped`
  (clear `_pending_interrupt` if `speech_duration_ms < min_barge_in_speech_duration_ms`, default
  **1200 ms**); (2) an **`is_user_speaking` guard** in `_execute_confirmed_interrupt` (discard a
  pending interrupt if the user already stopped). The `is_user_speaking` guard is the reliable
  primary fix; the duration filter is the secondary preemptive one. Real barge-ins are ≥1.5–2 s;
  noise bursts are <1 s. Env (example): `<FEATURE>__SESSION__MIN_BARGE_IN_SPEECH_DURATION_MS`.
- **H3 gate** (AI interrupting during long answers): gate premature `response.created` on the **last
  speech segment duration** (`audio_end_ms − audio_start_ms`), NOT elapsed time (which is dominated
  by model processing). Reject if the last segment was short (<~1000 ms = VAD phrase-boundary false
  positive). Disabled when `min_speech_duration_before_ai_response_ms=0`.
- **Rejecting a `response.created`** can't stop already-queued deltas. Track `_rejected_response_ids`;
  on reject, add `event.response.id`; in delta handlers, early-return if `response_id` OR `item_id`
  is in the set (OpenAI events may use either); on `response.canceled`, do minimal cleanup only.
- **Never gate frontend audio** to fight barge-ins (see §3).

## 3. Audio-stream continuity: never stop sending, never leave gaps

- OpenAI VAD (both modes) needs a **continuous audio stream**. Never stop sending `AUDIO_DATA` during
  AI speech and never set mic gain to 0 — that disables VAD and kills barge-in. WebSocket transport
  has no native mute.
- For echo: browser `echoCancellation: true`, OpenAI server-side `far_field` noise reduction, and a
  *moderate* soft gain reduction (~0.2–0.3, −10 to −14 dB). The real defense is the §2 backend
  filters, not frontend gating.
- Any future logic that *drops* audio chunks must **replace them with silence PCM** (zeros, same
  format) — gaps break VAD/barge-in. "Empty data" = valid silence PCM, not `b""`/no transmission.

## 4. Reconnect resilience

- A **write-path socket failure** can occur before the read loop notices the socket is dead. The
  write handler must actively **downgrade local health**: mark service unconfigured, clear
  `connection_ready`, set `DISCONNECTED`, close the provider connection WITHOUT
  `_explicit_close_requested`, and let the realtime connection manager's read-loop drive reconnect.
  Do NOT call full session re-init from the send path (duplicates long-lived streaming tasks).
- **Preserve buffered mic audio across reconnects.** Do not clear `audio_stream.input_buffer` in
  `_handle_session_created()` on reconnection — that discards speech spoken during the outage. Let
  the stream layer replay buffered audio into the new session.
- **Session-scoped transcript providers must survive reconnects** — re-bind them to the new
  connection rather than recreating per-connection.

## 5. Event names and shapes (verify against SDK source)

- Use **standard event names**: `response.output_audio.delta` / `.done`,
  `response.output_audio_transcript.delta` / `.done` — NOT the legacy `response.audio.*`. Handlers
  registered for legacy names silently never fire. (WebRTC vs WebSocket transports may differ;
  WebSocket uses standard names.) Rollback lever: `REALTIME_MODEL=gpt-realtime`.
- **Delta events use a flat `response_id: str`**, NOT a nested `response` object. Only *lifecycle*
  events (`ResponseCreatedEvent`, `ResponseDoneEvent`) carry the nested `response`. A typed Protocol
  that declares `response` on delta events is wrong and yields `AttributeError` → 0 bytes recorded.

## 6. Session config: reasoning, capability recovery, per-response overrides

- **Reasoning is nested**: `session.reasoning = {"effort": <minimal|low|medium|high|xhigh>}`. There
  is NO top-level `session.reasoning_effort` (GA schema). Gate with `is not None`. Keep a regression
  assertion that the WRONG shape is ABSENT (`assert "reasoning_effort" not in payload`) — mocked
  boundary tests will otherwise encode an invalid wire contract that the real API rejects.
- **Capability-field rejections are async error events**, not sync exceptions. Recover by
  **strip-and-reconfigure**, not retry: classify on **`code` == `unknown_parameter`** (not message
  text) → `RECOVERABLE_SESSION_PARAM`; keep a per-model `_disabled_session_keys` cache; re-send
  `session.update` under the configure lock with `is_configured` reset. Guard with (a) an
  **allowlist** of strippable optional keys (`reasoning`, `tools`, `tool_choice`, `noise_reduction`)
  — core keys (`instructions`, `type`, `audio`) stay fatal; (b) a strip cap counted BEFORE the
  attempt (`REALTIME_MAX_CAPABILITY_STRIP_ATTEMPTS`) so a throwing reconfigure can't loop; (c) a
  fall-through to the fatal path so worst case == prior behavior.
- **`response.create` `instructions` OVERRIDE the session system prompt** for that one response
  (only conversation history survives). A per-response template that drives content *selection*
  (e.g. "ask the next question on a different competency") must be self-contained against history or
  inject the needed state. Templates that only *transform existing content* (e.g. rephrase the
  previous question) are safe.
- **The model self-drives every turn — there is NO cheap per-turn code injection.** With
  `turn_detection.create_response=true` the model auto-creates each response from session
  instructions + the FULL conversation history (it conditions on audio items even with
  `input_audio_transcription` disabled — that knob only affects our text copy). Normal questions are
  never code-injected (only the greeting trigger and the two override handlers send
  `response.create`). So "the AI doesn't listen" is a PROMPT problem (anchor mass), and every
  per-turn injection lever is LOSSY per the SDK types: `instructions` replaces the session prompt,
  `input` replaces conversation context, `conversation:"none"` is out-of-band. A genuine
  per-turn-code requirement means `create_response:false` + manual item injection + manual
  `response.create` — a spec-gated session-mode change that IS the planner architecture, not a
  tweak. Durable behavior changes go through `session.update`.
- **User-triggered overrides fire in lifecycle states their text never anticipated** — post-close,
  pre-first-question, mid-goodbye — and because the override replaces ALL session rules (including
  the closing protocol), whatever it commands wins in that state (a post-close Skip re-opened a
  finished session). Enumerate session-state × override-text when writing or reviewing one; prefer
  gating the trigger by state in code/UI. When diagnosing "the AI ignored its closing/opening
  rules", check whether an override turn was the actual actor before blaming the base prompt.
- **Any NEW stateful content added to session instructions is invisible during every override.**
  The corollary of "overrides replace session instructions": each time a feature adds state to the
  session prompt (a retake coverage map, personalization, agenda state), every existing
  `override_in_flight_response` template becomes a blind spot for it and must be re-audited —
  either augmented with a compact digest of the new state, or shown not to need it (ask-differently
  rephrases the same question → no topic selection → safe; skip selects the next question → needs
  the digest). Treat "session instructions gained new state" as a trigger to enumerate all
  `override_in_flight_response` call sites and record an augment-vs-safe decision for each.
- **Under `create_response=true`, a prompt "stop and wait" is unimplementable.** The API auto-creates
  a response after every detected candidate utterance, so an instruction to be silent gives the
  forced response no legal output and the model reverts to its dominant trained pattern in that
  prompt — for us, asking a question (the mains mandate "The question is ALWAYS the last element"
  and Error Handling prescribes "[Brief answer]. Now, [next question]"). This produced 39 post-close
  questions in one weekly window across 6/79 sessions. Two consequences: (1) **every** reachable
  conversation state, including terminal ones, needs a positively specified reply shape
  (condition→output), never a "be silent" instruction; (2) a state-scoped ban added to a large prompt
  must NAME and explicitly override the pre-existing rules that fire on the same trigger — positional
  recency and specificity alone did not hold here (the standing "no new question after the close"
  rule existed and demonstrably failed).
- **`reasoning` omission may be model-dependent — do not rely on the default either way.** 1.x
  realtime models (`gpt-realtime`, `-mini`, `-1.5`) have no reasoning support at all. For
  gpt-realtime-2.x there is a **reported but unconfirmed** default of effort `low` when the session
  omits the key — the only source is a DevForum responder ("sps",
  community.openai.com/t/gpt-realtime-model-default-reasoning/1387803, 2026-07-22) whose OpenAI
  affiliation is *implied by wording but not verifiable*, and it is absent from the official docs;
  the thread was re-read 2026-07-27 but **the behavior itself has never been measured here.** Treat
  it as a hypothesis, not a fact. What follows regardless: a model bump can silently change latency
  and conduct for key-omitting sessions, so **pin `reasoning` effort explicitly per feature** rather
  than depending on any default. Confirming the 2.x default properly needs an A/B against a pinned-`low` session, not another
  doc lookup.
- **The model does not hold the session's configured language — it mirrors the speaker.** The
  prompt language is a preference, not a constraint: one non-English answer flips the assistant
  into that language for the remainder (with occasional fragments of the original resurfacing). Any
  downstream consumer pinned to the configured language (Deepgram STT `language=en`) then silently
  loses the session, and the drift is invisible in logs — conversation flow, VAD, and turn cadence
  all look healthy. Features depending on the configured language need either prompt-hardening that
  makes the assistant hold/redirect, or tolerance for drift.

## 7. Pacing: the model has no clock

The Realtime model receives **no runtime time signal** — elapsed/remaining minutes are never
injected. Every wall-clock instruction ("~35 minutes", "X minutes left") is inert. **Pace by
coverage and question/turn count**, not time. Avoid "top N questions" caps that silently bound
length. Gate any closing/wrap-up protocol on explicit coverage + minimum-count conditions, placed at
BOTH primacy and recency (a lone middle-of-prompt number is unreliable).

## 8. Benign errors

- `conversation_already_has_active_response` in the first ~2–3 s of a session is almost always an
  echo-triggered VAD false positive (mic picks up the initial greeting with
  `turn_detection_create_response: true`). Classify as `BENIGN_RACE_CONDITION` — the original
  response completes; no recovery needed. Outside session start, investigate response management.

## Cross-references
- Architectural session-mode changes (VAD type, audio model) are architectural decisions, not
  configuration changes — they require a spec.
- A shared realtime session config contract used by multiple voice features (e.g. a
  `RealtimeConfigProtocol`) — changes need ≥ a Medium spec.
- For model IDs / parameter shapes, fetch the SDK type source via `ai-docs-lookup` before answering.
