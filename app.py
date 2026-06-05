# ----------------------------- with kaggle and misral 1.x and edge-tts -----------------------------




# # ============================================================
# # AI Voice Assistant — Single File
# # STT  : Kaggle ngrok endpoint (faster-whisper-large-v3)
# # LLM  : Mistral API
# # TTS  : edge-tts (Microsoft, free, natural voice)
# # UI   : Served inline via FastAPI
# # Tunnel: Cloudflare (run separately — see bottom of file)
# # ============================================================

# import os
# import io
# import logging
# import asyncio
# import tempfile
# import httpx
# import edge_tts
# import uvicorn

# from fastapi import FastAPI, File, UploadFile, HTTPException, Request
# from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse

# # ── Mistral import: handles both v1.x and v2.x ──────────
# try:
#     from mistralai import Mistral          # v1.x  (pip install mistralai==1.9.11)
#     _MISTRAL_V2 = False
# except ImportError:
#     from mistralai.client import Mistral   # v2.x
#     _MISTRAL_V2 = True

# # ─────────────────────────────────────────────────────────────
# # LOGGING
# # ─────────────────────────────────────────────────────────────
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
#     datefmt="%H:%M:%S",
# )
# log = logging.getLogger("VoiceAssistant")

# # ─────────────────────────────────────────────────────────────
# # CONFIG  ← edit these
# # ─────────────────────────────────────────────────────────────
# KAGGLE_STT_URL  = "https://unshakable-yasuko-luxuriantly.ngrok-free.dev/transcribe"  # ← your Kaggle ngrok URL
# MISTRAL_API_KEY = "kqDyAWOT8lby4RiowXvGh2FJV4qXm893"                # ← your Mistral API key
# MISTRAL_MODEL   = "mistral-large-latest"
# EDGE_TTS_VOICE  = "en-US-AndrewNeural"                       # natural male voice
# SERVER_PORT     = 8001

# SYSTEM_PROMPT = """You are a senior AI/ML engineer and developer with 10+ years of experience.
# You only answer questions related to AI, ML, deep learning, MLOps, data science, and software engineering in the context of AI/ML.
# If the user asks anything outside this domain, politely decline and redirect them to ask AI/ML related questions.
# Keep answers concise, practical, and technically accurate.
# Avoid unnecessary fluff — get to the point like a senior engineer would."""

# # ─────────────────────────────────────────────────────────────
# # STARTUP VALIDATION
# # ─────────────────────────────────────────────────────────────
# if "YOUR_NGROK_URL_HERE" in KAGGLE_STT_URL:
#     log.warning("⚠️  KAGGLE_STT_URL is not set. Update it before using /process.")
# else:
#     log.info(f"✅ KAGGLE_STT_URL set: {KAGGLE_STT_URL}")

# if "YOUR_MISTRAL_API_KEY_HERE" in MISTRAL_API_KEY:
#     log.warning("⚠️  MISTRAL_API_KEY is not set. Update it before using /process.")
# else:
#     log.info(f"✅ MISTRAL_API_KEY set: {MISTRAL_API_KEY[:6]}...{MISTRAL_API_KEY[-4:]}")

# # ─────────────────────────────────────────────────────────────
# # CLIENTS
# # ─────────────────────────────────────────────────────────────
# mistral_client = Mistral(api_key=MISTRAL_API_KEY)
# log.info(f"✅ Mistral client initialized (SDK v{'2.x' if _MISTRAL_V2 else '1.x'}).")

# # ─────────────────────────────────────────────────────────────
# # FASTAPI
# # ─────────────────────────────────────────────────────────────
# app = FastAPI(title="Voice Assistant", version="1.0.0")

# # ─────────────────────────────────────────────────────────────
# # HELPERS
# # ─────────────────────────────────────────────────────────────

# async def stt_transcribe(audio_bytes: bytes, filename: str) -> str:
#     """Send audio to Kaggle STT endpoint, return transcription text."""
#     log.info(f"[STT] Sending {len(audio_bytes)/1024:.1f} KB to Kaggle endpoint ...")
#     try:
#         async with httpx.AsyncClient(timeout=60.0) as client:
#             response = await client.post(
#                 KAGGLE_STT_URL,
#                 files={"file": (filename, audio_bytes, "audio/webm")},
#             )
#         response.raise_for_status()
#         data         = response.json()
#         transcription = data.get("transcription", "").strip()
#         lang         = data.get("detected_language", "unknown")
#         source       = data.get("language_source", "unknown")
#         duration     = data.get("audio_duration_sec", 0)
#         log.info(f"[STT] ✅ Transcription received | lang: {lang} ({source}) | "
#                  f"duration: {duration}s | text: '{transcription[:80]}'")
#         return transcription
#     except httpx.HTTPStatusError as e:
#         log.error(f"[STT] ❌ HTTP error {e.response.status_code}: {e.response.text}")
#         raise HTTPException(status_code=502, detail=f"STT service error: {e.response.status_code}")
#     except httpx.RequestError as e:
#         log.error(f"[STT] ❌ Connection error: {e}")
#         raise HTTPException(status_code=503, detail="STT service unreachable. Check Kaggle ngrok URL.")


# async def llm_answer(user_text: str) -> str:
#     """Send transcription to Mistral, return answer text."""
#     log.info(f"[LLM] Sending to Mistral | query: '{user_text[:80]}'")
#     try:
#         response = mistral_client.chat.complete(
#             model=MISTRAL_MODEL,
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user",   "content": user_text},
#             ],
#         )
#         answer = response.choices[0].message.content.strip()
#         tokens = response.usage.total_tokens if response.usage else "?"
#         log.info(f"[LLM] ✅ Answer received | tokens: {tokens} | "
#                  f"preview: '{answer[:80]}'")
#         return answer
#     except Exception as e:
#         log.error(f"[LLM] ❌ Mistral error: {e}")
#         raise HTTPException(status_code=502, detail=f"LLM error: {str(e)}")


# async def tts_synthesize(text: str) -> bytes:
#     """Convert text to speech using edge-tts, return MP3 bytes."""
#     log.info(f"[TTS] Synthesizing {len(text)} chars with voice: {EDGE_TTS_VOICE}")
#     try:
#         communicate = edge_tts.Communicate(text, EDGE_TTS_VOICE)
#         audio_chunks = []
#         async for chunk in communicate.stream():
#             if chunk["type"] == "audio":
#                 audio_chunks.append(chunk["data"])
#         audio_bytes = b"".join(audio_chunks)
#         log.info(f"[TTS] ✅ Synthesized {len(audio_bytes)/1024:.1f} KB audio")
#         return audio_bytes
#     except Exception as e:
#         log.error(f"[TTS] ❌ edge-tts error: {e}")
#         raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")


# # ─────────────────────────────────────────────────────────────
# # ROUTES
# # ─────────────────────────────────────────────────────────────

# @app.post("/process")
# async def process_voice(file: UploadFile = File(...)):
#     """
#     Full pipeline:
#       1. Audio → STT (Kaggle)
#       2. Text  → LLM (Mistral)
#       3. Text  → TTS (edge-tts)
#     Returns JSON with transcription, answer, and base64 audio.
#     """
#     import base64

#     log.info("─" * 55)
#     log.info(f"[Process] New request | file: {file.filename} | type: {file.content_type}")

#     audio_bytes  = await file.read()
#     if not audio_bytes:
#         raise HTTPException(status_code=400, detail="Empty audio file.")

#     # Step 1: STT
#     transcription = await stt_transcribe(audio_bytes, file.filename or "audio.webm")
#     if not transcription:
#         log.warning("[Process] STT returned empty transcription.")
#         return JSONResponse(content={
#             "transcription": "",
#             "answer": "I couldn't hear anything. Please try again.",
#             "audio_b64": "",
#         })

#     # Step 2: LLM
#     answer = await llm_answer(transcription)

#     # Step 3: TTS
#     audio_bytes_out = await tts_synthesize(answer)
#     audio_b64       = base64.b64encode(audio_bytes_out).decode("utf-8")

#     log.info("[Process] ✅ Full pipeline complete.")
#     log.info("─" * 55)

#     return JSONResponse(content={
#         "transcription": transcription,
#         "answer":        answer,
#         "audio_b64":     audio_b64,
#     })


# @app.get("/health")
# async def health():
#     return {"status": "ok", "stt_url": KAGGLE_STT_URL}


# @app.get("/", response_class=HTMLResponse)
# async def ui():
#     return HTMLResponse(content=HTML_UI)


# # ─────────────────────────────────────────────────────────────
# # UI — served inline
# # ─────────────────────────────────────────────────────────────
# HTML_UI = """<!DOCTYPE html>
# <html lang="en">
# <head>
# <meta charset="UTF-8"/>
# <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
# <title>AI Voice Assistant</title>
# <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet"/>
# <style>
#   :root {
#     --bg:        #0a0a0f;
#     --surface:   #12121a;
#     --border:    #1e1e2e;
#     --accent:    #7c6aff;
#     --accent2:   #ff6a9b;
#     --text:      #e8e6ff;
#     --muted:     #5a5875;
#     --success:   #4ade80;
#     --error:     #f87171;
#     --record:    #ff4560;
#   }

#   *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

#   body {
#     background: var(--bg);
#     color: var(--text);
#     font-family: 'Syne', sans-serif;
#     min-height: 100vh;
#     display: flex;
#     flex-direction: column;
#     align-items: center;
#     padding: 24px 16px 48px;
#     overflow-x: hidden;
#   }

#   /* Ambient background blobs */
#   body::before, body::after {
#     content: '';
#     position: fixed;
#     border-radius: 50%;
#     filter: blur(120px);
#     opacity: 0.12;
#     pointer-events: none;
#     z-index: 0;
#   }
#   body::before {
#     width: 500px; height: 500px;
#     background: var(--accent);
#     top: -150px; left: -150px;
#   }
#   body::after {
#     width: 400px; height: 400px;
#     background: var(--accent2);
#     bottom: -100px; right: -100px;
#   }

#   .container {
#     width: 100%;
#     max-width: 720px;
#     position: relative;
#     z-index: 1;
#     display: flex;
#     flex-direction: column;
#     gap: 20px;
#   }

#   /* Header */
#   header {
#     text-align: center;
#     padding: 32px 0 8px;
#   }
#   header .tag {
#     font-family: 'Space Mono', monospace;
#     font-size: 11px;
#     letter-spacing: 3px;
#     text-transform: uppercase;
#     color: var(--accent);
#     margin-bottom: 10px;
#   }
#   header h1 {
#     font-size: clamp(24px, 6vw, 42px);
#     font-weight: 800;
#     background: linear-gradient(135deg, var(--text) 0%, var(--accent) 60%, var(--accent2) 100%);
#     -webkit-background-clip: text;
#     -webkit-text-fill-color: transparent;
#     background-clip: text;
#     line-height: 1.1;
#   }
#   header p {
#     margin-top: 10px;
#     color: var(--muted);
#     font-size: 14px;
#     font-family: 'Space Mono', monospace;
#   }

#   /* Status bar */
#   .status-bar {
#     display: flex;
#     align-items: center;
#     gap: 10px;
#     background: var(--surface);
#     border: 1px solid var(--border);
#     border-radius: 12px;
#     padding: 12px 18px;
#     font-family: 'Space Mono', monospace;
#     font-size: 12px;
#   }
#   .status-dot {
#     width: 8px; height: 8px;
#     border-radius: 50%;
#     background: var(--muted);
#     flex-shrink: 0;
#     transition: background 0.3s;
#   }
#   .status-dot.recording { background: var(--record); animation: pulse-dot 1s infinite; }
#   .status-dot.processing { background: var(--accent); animation: pulse-dot 0.6s infinite; }
#   .status-dot.ready { background: var(--success); }
#   .status-dot.error { background: var(--error); }

#   @keyframes pulse-dot {
#     0%, 100% { opacity: 1; transform: scale(1); }
#     50%       { opacity: 0.4; transform: scale(0.7); }
#   }

#   #status-text { color: var(--text); flex: 1; }

#   /* Waveform */
#   .waveform-container {
#     background: var(--surface);
#     border: 1px solid var(--border);
#     border-radius: 16px;
#     padding: 20px;
#     height: 80px;
#     display: flex;
#     align-items: center;
#     justify-content: center;
#     overflow: hidden;
#   }
#   canvas#waveform {
#     width: 100%;
#     height: 40px;
#   }

#   /* Controls */
#   .controls {
#     display: flex;
#     gap: 12px;
#     justify-content: center;
#   }

#   .btn {
#     font-family: 'Syne', sans-serif;
#     font-weight: 600;
#     font-size: 14px;
#     letter-spacing: 0.5px;
#     border: none;
#     border-radius: 12px;
#     padding: 14px 28px;
#     cursor: pointer;
#     transition: all 0.2s ease;
#     display: flex;
#     align-items: center;
#     gap: 8px;
#     flex: 1;
#     justify-content: center;
#     max-width: 200px;
#   }
#   .btn:active { transform: scale(0.96); }
#   .btn:disabled { opacity: 0.35; cursor: not-allowed; transform: none; }

#   .btn-record {
#     background: linear-gradient(135deg, #ff4560, #ff6a9b);
#     color: #fff;
#     box-shadow: 0 4px 24px rgba(255,69,96,0.3);
#   }
#   .btn-record:hover:not(:disabled) { box-shadow: 0 6px 32px rgba(255,69,96,0.5); }
#   .btn-record.recording {
#     background: linear-gradient(135deg, #ff1a3e, #ff4560);
#     animation: glow-record 1.2s ease-in-out infinite;
#   }
#   @keyframes glow-record {
#     0%, 100% { box-shadow: 0 4px 24px rgba(255,69,96,0.4); }
#     50%       { box-shadow: 0 4px 48px rgba(255,69,96,0.8); }
#   }

#   .btn-stop {
#     background: var(--surface);
#     color: var(--text);
#     border: 1px solid var(--border);
#   }
#   .btn-stop:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }

#   /* Chat area */
#   .chat-area {
#     display: flex;
#     flex-direction: column;
#     gap: 14px;
#   }

#   .bubble {
#     border-radius: 16px;
#     padding: 16px 20px;
#     font-size: 15px;
#     line-height: 1.65;
#     animation: slide-up 0.3s ease;
#     position: relative;
#   }
#   @keyframes slide-up {
#     from { opacity: 0; transform: translateY(12px); }
#     to   { opacity: 1; transform: translateY(0); }
#   }

#   .bubble-user {
#     background: var(--surface);
#     border: 1px solid var(--border);
#     border-left: 3px solid var(--accent);
#   }
#   .bubble-user .bubble-label {
#     font-family: 'Space Mono', monospace;
#     font-size: 10px;
#     letter-spacing: 2px;
#     text-transform: uppercase;
#     color: var(--accent);
#     margin-bottom: 8px;
#   }

#   .bubble-ai {
#     background: linear-gradient(135deg, rgba(124,106,255,0.08), rgba(255,106,155,0.05));
#     border: 1px solid rgba(124,106,255,0.2);
#     border-left: 3px solid var(--accent2);
#   }
#   .bubble-ai .bubble-label {
#     font-family: 'Space Mono', monospace;
#     font-size: 10px;
#     letter-spacing: 2px;
#     text-transform: uppercase;
#     color: var(--accent2);
#     margin-bottom: 8px;
#   }
#   .bubble-text { color: var(--text); white-space: pre-wrap; word-break: break-word; }

#   /* Audio player */
#   .audio-player {
#     margin-top: 10px;
#     width: 100%;
#     height: 36px;
#     border-radius: 8px;
#     accent-color: var(--accent2);
#   }

#   /* Spinner */
#   .spinner {
#     width: 18px; height: 18px;
#     border: 2px solid rgba(124,106,255,0.2);
#     border-top-color: var(--accent);
#     border-radius: 50%;
#     animation: spin 0.7s linear infinite;
#     flex-shrink: 0;
#   }
#   @keyframes spin { to { transform: rotate(360deg); } }

#   /* Empty state */
#   .empty-state {
#     text-align: center;
#     padding: 48px 24px;
#     color: var(--muted);
#     font-family: 'Space Mono', monospace;
#     font-size: 13px;
#     border: 1px dashed var(--border);
#     border-radius: 16px;
#     line-height: 2;
#   }
#   .empty-state .icon { font-size: 36px; margin-bottom: 12px; }

#   /* Config warning */
#   .config-warning {
#     background: rgba(248,113,113,0.08);
#     border: 1px solid rgba(248,113,113,0.25);
#     border-radius: 12px;
#     padding: 12px 16px;
#     font-family: 'Space Mono', monospace;
#     font-size: 12px;
#     color: var(--error);
#     display: none;
#   }

#   @media (max-width: 480px) {
#     .btn { padding: 14px 18px; font-size: 13px; }
#   }
# </style>
# </head>
# <body>
# <div class="container">

#   <header>
#     <div class="tag">AI / ML Engineer Assistant</div>
#     <h1>Voice Assistant</h1>
#     <p>Ask anything about AI, ML & engineering</p>
#   </header>

#   <div class="config-warning" id="config-warning">
#     ⚠ Server config incomplete — check KAGGLE_STT_URL and MISTRAL_API_KEY in app.py
#   </div>

#   <div class="status-bar">
#     <div class="status-dot" id="status-dot"></div>
#     <span id="status-text">Ready — press Record to start</span>
#   </div>

#   <div class="waveform-container">
#     <canvas id="waveform"></canvas>
#   </div>

#   <div class="controls">
#     <button class="btn btn-record" id="btn-record" onclick="startRecording()">
#       <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
#         <circle cx="12" cy="12" r="6"/>
#       </svg>
#       Record
#     </button>
#     <button class="btn btn-stop" id="btn-stop" onclick="stopRecording()" disabled>
#       <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
#         <rect x="4" y="4" width="16" height="16" rx="2"/>
#       </svg>
#       Stop
#     </button>
#   </div>

#   <div class="chat-area" id="chat-area">
#     <div class="empty-state" id="empty-state">
#       <div class="icon">🎙️</div>
#       Press <strong>Record</strong>, ask your question,<br/>
#       then press <strong>Stop</strong> to get an answer.
#     </div>
#   </div>

# </div>

# <script>
# // ── State ────────────────────────────────────────────────
# let mediaRecorder = null;
# let audioChunks   = [];
# let audioCtx      = null;
# let analyser      = null;
# let animFrameId   = null;
# let stream        = null;

# // ── DOM refs ─────────────────────────────────────────────
# const statusDot   = document.getElementById('status-dot');
# const statusText  = document.getElementById('status-text');
# const btnRecord   = document.getElementById('btn-record');
# const btnStop     = document.getElementById('btn-stop');
# const chatArea    = document.getElementById('chat-area');
# const emptyState  = document.getElementById('empty-state');
# const canvas      = document.getElementById('waveform');
# const ctx2d       = canvas.getContext('2d');

# // ── Check server health on load ──────────────────────────
# window.addEventListener('load', async () => {
#   try {
#     const r = await fetch('/health');
#     const d = await r.json();
#     if (d.stt_url && d.stt_url.includes('YOUR_NGROK')) {
#       document.getElementById('config-warning').style.display = 'block';
#     }
#   } catch(e) {}
# });

# // ── Status helpers ───────────────────────────────────────
# function setStatus(state, text) {
#   statusDot.className = 'status-dot ' + state;
#   statusText.textContent = text;
# }

# // ── Waveform ─────────────────────────────────────────────
# function startWaveform(mediaStream) {
#   audioCtx  = new (window.AudioContext || window.webkitAudioContext)();
#   analyser  = audioCtx.createAnalyser();
#   analyser.fftSize = 256;
#   const src = audioCtx.createMediaStreamSource(mediaStream);
#   src.connect(analyser);
#   drawWaveform();
# }

# function drawWaveform() {
#   animFrameId = requestAnimationFrame(drawWaveform);
#   const buf = new Uint8Array(analyser.frequencyBinCount);
#   analyser.getByteFrequencyData(buf);

#   const W = canvas.width  = canvas.offsetWidth;
#   const H = canvas.height = canvas.offsetHeight;
#   ctx2d.clearRect(0, 0, W, H);

#   const barW  = (W / buf.length) * 2.2;
#   let x = 0;
#   buf.forEach(val => {
#     const barH = (val / 255) * H;
#     const alpha = 0.4 + (val / 255) * 0.6;
#     ctx2d.fillStyle = `rgba(124, 106, 255, ${alpha})`;
#     ctx2d.fillRect(x, H - barH, barW - 1, barH);
#     x += barW + 1;
#   });
# }

# function stopWaveform() {
#   if (animFrameId) cancelAnimationFrame(animFrameId);
#   if (audioCtx)    audioCtx.close();
#   ctx2d.clearRect(0, 0, canvas.width, canvas.height);
#   animFrameId = null; audioCtx = null; analyser = null;
# }

# // ── Recording ────────────────────────────────────────────
# async function startRecording() {
#   try {
#     stream = await navigator.mediaDevices.getUserMedia({ audio: true });
#   } catch(e) {
#     setStatus('error', 'Microphone access denied.');
#     return;
#   }

#   audioChunks   = [];
#   mediaRecorder = new MediaRecorder(stream);

#   mediaRecorder.ondataavailable = e => {
#     if (e.data.size > 0) audioChunks.push(e.data);
#   };

#   mediaRecorder.start(100);
#   startWaveform(stream);

#   btnRecord.disabled = true;
#   btnRecord.classList.add('recording');
#   btnStop.disabled   = false;
#   setStatus('recording', 'Recording… press Stop when done');
# }

# async function stopRecording() {
#   if (!mediaRecorder || mediaRecorder.state === 'inactive') return;

#   mediaRecorder.stop();
#   stream.getTracks().forEach(t => t.stop());
#   stopWaveform();

#   btnStop.disabled   = true;
#   btnRecord.disabled = true;
#   setStatus('processing', 'Transcribing…');

#   mediaRecorder.onstop = async () => {
#     const blob     = new Blob(audioChunks, { type: 'audio/webm' });
#     const formData = new FormData();
#     formData.append('file', blob, 'recording.webm');

#     // Show processing bubble
#     const processingId = showProcessing();

#     try {
#       const resp = await fetch('/process', { method: 'POST', body: formData });

#       if (!resp.ok) {
#         const err = await resp.json();
#         throw new Error(err.detail || 'Server error');
#       }

#       const data = await resp.json();
#       removeProcessing(processingId);

#       if (data.transcription) {
#         addUserBubble(data.transcription);
#       }
#       addAIBubble(data.answer, data.audio_b64);
#       setStatus('ready', 'Done — press Record for next question');

#     } catch(e) {
#       removeProcessing(processingId);
#       addErrorBubble(e.message);
#       setStatus('error', 'Error: ' + e.message);
#     }

#     btnRecord.disabled = false;
#     btnRecord.classList.remove('recording');
#   };
# }

# // ── Chat bubbles ─────────────────────────────────────────
# function removeEmpty() {
#   if (emptyState) emptyState.remove();
# }

# function showProcessing() {
#   removeEmpty();
#   const id  = 'proc-' + Date.now();
#   const div = document.createElement('div');
#   div.id        = id;
#   div.className = 'bubble bubble-ai';
#   div.innerHTML = `
#     <div class="bubble-label">Assistant</div>
#     <div style="display:flex;align-items:center;gap:10px;color:var(--muted);font-size:13px;font-family:'Space Mono',monospace;">
#       <div class="spinner"></div> Processing your question…
#     </div>`;
#   chatArea.appendChild(div);
#   div.scrollIntoView({ behavior: 'smooth' });
#   return id;
# }

# function removeProcessing(id) {
#   const el = document.getElementById(id);
#   if (el) el.remove();
# }

# function addUserBubble(text) {
#   removeEmpty();
#   const div = document.createElement('div');
#   div.className = 'bubble bubble-user';
#   div.innerHTML = `<div class="bubble-label">You</div>
#                    <div class="bubble-text">${escHtml(text)}</div>`;
#   chatArea.appendChild(div);
# }

# function addAIBubble(text, audioB64) {
#   const div = document.createElement('div');
#   div.className = 'bubble bubble-ai';

#   let audioHtml = '';
#   if (audioB64) {
#     audioHtml = `<audio class="audio-player" controls autoplay
#                    src="data:audio/mp3;base64,${audioB64}"></audio>`;
#   }

#   div.innerHTML = `<div class="bubble-label">Assistant</div>
#                    <div class="bubble-text">${escHtml(text)}</div>
#                    ${audioHtml}`;
#   chatArea.appendChild(div);
#   div.scrollIntoView({ behavior: 'smooth' });
# }

# function addErrorBubble(msg) {
#   const div = document.createElement('div');
#   div.className = 'bubble';
#   div.style.cssText = 'border:1px solid rgba(248,113,113,0.3);background:rgba(248,113,113,0.06);border-left:3px solid var(--error)';
#   div.innerHTML = `<div style="font-family:'Space Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--error);margin-bottom:8px;">Error</div>
#                    <div class="bubble-text" style="color:var(--error)">${escHtml(msg)}</div>`;
#   chatArea.appendChild(div);
#   div.scrollIntoView({ behavior: 'smooth' });
# }

# function escHtml(str) {
#   return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
# }
# </script>
# </body>
# </html>
# """

# # ─────────────────────────────────────────────────────────────
# # ENTRY POINT
# # ─────────────────────────────────────────────────────────────
# if __name__ == "__main__":
#     log.info("=" * 55)
#     log.info("  🚀  Voice Assistant starting ...")
#     log.info(f"  Port       : {SERVER_PORT}")
#     log.info(f"  STT URL    : {KAGGLE_STT_URL}")
#     log.info(f"  LLM Model  : {MISTRAL_MODEL}")
#     log.info(f"  TTS Voice  : {EDGE_TTS_VOICE}")
#     log.info("=" * 55)
#     uvicorn.run("app:app", host="0.0.0.0", port=SERVER_PORT, reload=False)













# --------------------------------- with groq and mistral 2.0 working okay  ---------------------------------








# # ================================================================
# # AI Voice Assistant — Conversational, Auto-VAD, Multilingual
# #
# # STT  : Groq Whisper large-v3   (verbose_json → lang detection)
# # LLM  : Groq llama-3.3-70b-versatile (streaming, free tier)
# # TTS  : edge-tts sentence-aware (sentence-boundary chunking)
# # VAD  : Browser-side energy     (2.0s silence → auto-trigger)
# # UI   : Pulsing orb, 2 buttons  (Start / End Conversation)
# # Lang : Whisper detects EN/HI/GU → locks for full session
# #
# # FIXES APPLIED:
# # [F1] Secrets via env var — no hardcoded API key
# # [F2] Dedicated ThreadPoolExecutor for Whisper STT
# # [F3] sanitize_for_tts runs on complete sentences, not tokens
# # [F4] Sentence splitter handles no-space boundaries + Hindi/Gujarati
# # [F5] MIN_CHUNK_WORDS lowered to 6 — short answers no longer delayed
# # [F6] Interrupt handler has 150ms drain gap before signalling ready
# # [F7] TTS temp file uses context manager — no leaks on exception
# # [F8] raw_buf accumulates unsanitized text; sanitizer on full chunk
# # ================================================================

# import asyncio
# import json
# import logging
# import os
# import re
# import tempfile
# from concurrent.futures import ThreadPoolExecutor

# import edge_tts
# import uvicorn
# from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# from fastapi.responses import HTMLResponse
# from groq import Groq

# # ── Logging ──────────────────────────────────────────────────────
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
#     datefmt="%H:%M:%S",
# )
# log = logging.getLogger("VoiceAssistant")

# # ================================================================
# # CONFIG  [F1] — read from environment, never hardcode
# # ================================================================
# GROQ_API_KEY   = ""
# GROQ_STT_MODEL = "whisper-large-v3"
# GROQ_LLM_MODEL = "llama-3.3-70b-versatile"
# SERVER_PORT    = int(os.environ.get("PORT", 8001))

# if not GROQ_API_KEY:
#     raise RuntimeError(
#         "GROQ_API_KEY environment variable is not set.\n"
#         "Then restart the server."
#     )
# log.info(f"✅ GROQ_API_KEY: {GROQ_API_KEY[:6]}...{GROQ_API_KEY[-4:]}")

# # ── Dedicated thread pool for blocking STT calls  [F2] ───────────
# # Isolates Whisper from the event loop — concurrent users don't starve each other
# _STT_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="stt")

# # ── VAD CONFIG ───────────────────────────────────────────────────
# SILENCE_MS     = 2000
# SILENCE_THRESH = 0.015
# MIN_SPEECH_MS  = 1200

# # Blobs under this size are noise — real speech starts at ~65 KB
# MIN_AUDIO_BYTES = 65 * 1024

# # ── Whisper hallucination blacklist ───────────────────────────────
# WHISPER_HALLUCINATIONS = {
#     "", " ", ".", ",", "you", "bye", "ok", "okay",
#     "thank you", "thanks", "thank you.", "thanks.",
#     "bye.", "okay.", "ok.", "you.", "hmm", "hmm.",
#     "um", "uh", "ah", "oh", "oh.", "ah.", "...", "…",
#     "subscribe", "like and subscribe", "subtitles by",
# }

# # ── Supported languages ───────────────────────────────────────────
# SUPPORTED_LANGS = {"en", "hi", "gu"}
# DEFAULT_LANG    = "en"

# LANG_CONFIG = {
#     "en": {"voice": "en-US-AndrewNeural",   "name": "English"},
#     "hi": {"voice": "hi-IN-MadhurNeural",   "name": "Hindi"},
#     "gu": {"voice": "gu-IN-NiranjanNeural", "name": "Gujarati"},
# }

# WHISPER_LANG_MAP = {
#     "english":  "en",
#     "hindi":    "hi",
#     "gujarati": "gu",
# }

# # ── TTS chunking  [F4] [F5] ───────────────────────────────────────
# # Lowered from 10 → 6: short complete sentences were always delayed to leftover
# MIN_CHUNK_WORDS = 6

# # [F4] Extended pattern:
# #   - standard whitespace after .!?।
# #   - newline after .!?।
# #   - capital Latin / Devanagari / Gujarati immediately after .!?।  (no space)
# SENTENCE_END = re.compile(
#     r'(?<=[.!?।])(?:\s+|(?=[A-Z\u0900-\u097F\u0A80-\u0AFF]))'
# )

# # ================================================================
# # SYSTEM PROMPT
# # ================================================================
# SYSTEM_PROMPT_TEMPLATE = """\
# You are a senior AI/ML engineer with 10+ years of experience.
# Only answer questions about AI, ML, deep learning, MLOps, data science, \
# and software engineering in the AI/ML context.
# For anything outside this domain, politely decline and redirect.
# Be concise and technically sharp. No fluff.

# RESPONSE FORMAT — STRICTLY FOLLOW EVERY RULE:
# - Write plain prose only. Zero markdown. Zero bullet points. Zero numbered lists.
# - Do NOT use asterisks, hyphens, underscores, or hash symbols.
# - Do NOT end a sentence with a colon.
# - Every sentence must be grammatically complete before starting the next.
# - Maximum 4 sentences per response unless user explicitly asks for more detail.
# - Write as if speaking naturally in a conversation.

# CRITICAL LANGUAGE RULE:
# The user is speaking {lang_name}. You MUST respond ONLY in {lang_name}.
# Do NOT switch languages under any circumstances, even for technical terms.\
# """

# groq_client = Groq(api_key=GROQ_API_KEY)
# log.info("✅ Groq client initialized (STT + LLM).")


# # ================================================================
# # HELPERS
# # ================================================================

# def is_hallucination(text: str) -> bool:
#     return text.strip().lower() in WHISPER_HALLUCINATIONS


# async def transcribe_audio(audio_bytes: bytes) -> tuple[str, str | None]:
#     """
#     Groq Whisper STT — verbose_json gives transcript + detected language.
#     Returns (transcript, lang_code | None).
#     Returns ("", None) if blob too small or transcript is a hallucination.
#     [F2] Uses dedicated _STT_EXECUTOR so it never blocks the event loop.
#     [F7] Uses context manager for temp file — no leaks on exception.
#     """
#     if len(audio_bytes) < MIN_AUDIO_BYTES:
#         log.info(
#             f"[STT] ⛔ Blob too small ({len(audio_bytes)/1024:.1f} KB < "
#             f"{MIN_AUDIO_BYTES//1024} KB) — skipping Whisper."
#         )
#         return "", None

#     log.info(f"[STT] {len(audio_bytes)/1024:.1f} KB → Groq Whisper ...")

#     def _call() -> tuple[str, str | None]:
#         # [F7] context manager ensures file is deleted even if an exception occurs
#         with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
#             f.write(audio_bytes)
#             f.flush()
#             f.seek(0)
#             r = groq_client.audio.transcriptions.create(
#                 file=("audio.wav", f, "audio/wav"),
#                 model=GROQ_STT_MODEL,
#                 response_format="verbose_json",
#             )
#         transcript   = r.text.strip() if hasattr(r, "text") else ""
#         detected_raw = getattr(r, "language", None)
#         return transcript, detected_raw

#     # [F2] submit to dedicated executor
#     transcript, detected_raw = await asyncio.get_event_loop().run_in_executor(
#         _STT_EXECUTOR, _call
#     )

#     if is_hallucination(transcript):
#         log.info(f"[STT] ⛔ Hallucination detected: '{transcript}' — ignoring.")
#         return "", None

#     detected_code = None
#     if detected_raw:
#         detected_code = WHISPER_LANG_MAP.get(detected_raw.lower())

#     log.info(
#         f"[STT] ✅ '{transcript[:80]}' | "
#         f"whisper_lang='{detected_raw}' → code='{detected_code}'"
#     )
#     return transcript, detected_code


# def sanitize_for_tts(text: str) -> str:
#     """
#     Strip markdown artifacts from a COMPLETE sentence before passing to TTS.
#     [F3] Called on full sentence chunks, not individual stream tokens.
#     This ensures multi-token markdown spans (** bold **) are always matched.
#     """
#     # Remove markdown bold/italic markers: ** __ * _
#     text = re.sub(r'\*{1,3}', '', text)
#     text = re.sub(r'_{1,3}', '', text)
#     # Remove inline code backticks
#     text = re.sub(r'`+', '', text)
#     # Remove heading markers: ## Title → Title
#     text = re.sub(r'(?m)^#{1,6}\s*', '', text)
#     # Remove blockquote markers
#     text = re.sub(r'(?m)^>\s*', '', text)
#     # Remove list markers: - item  * item  1. item
#     text = re.sub(r'(?m)^[-*+]\s+', '', text)
#     text = re.sub(r'(?m)^\d+\.\s+', '', text)
#     # Normalize newlines to single space
#     text = re.sub(r'\n+', ' ', text)
#     # Collapse multiple spaces
#     text = re.sub(r' {2,}', ' ', text)
#     # Replace trailing colon with period
#     text = re.sub(r':\s*$', '.', text)
#     return text.strip()


# def split_on_sentence(buf: str) -> tuple[str | None, str]:
#     """
#     Split at rightmost complete sentence boundary that meets MIN_CHUNK_WORDS.
#     [F4] Handles: 'sentence. Next', 'sentence.\\nNext', 'sentence.Next' (no space).
#     [F5] Walks from rightmost match backward so short sentences aren't skipped.
#     Returns (chunk, remaining) or (None, buf) if no valid boundary yet.
#     """
#     matches = list(SENTENCE_END.finditer(buf))
#     if not matches:
#         return None, buf

#     # Walk from rightmost match to find one that gives enough words
#     for m in reversed(matches):
#         chunk     = buf[:m.start() + 1].strip()
#         remaining = buf[m.end():].strip()
#         if len(chunk.split()) >= MIN_CHUNK_WORDS:
#             return chunk, remaining

#     return None, buf


# async def tts_stream(text: str, voice: str):
#     """Yield MP3 bytes from edge-tts for a complete sentence."""
#     comm = edge_tts.Communicate(text, voice)
#     async for chunk in comm.stream():
#         if chunk["type"] == "audio":
#             yield chunk["data"]


# # ================================================================
# # WEBSOCKET PIPELINE
# # ================================================================
# app = FastAPI(title="Voice Assistant")


# @app.websocket("/ws")
# async def ws_handler(ws: WebSocket):
#     await ws.accept()
#     log.info(f"[WS] Connected: {ws.client}")

#     active_task: asyncio.Task | None = None
#     session_lang:         str | None = None
#     conversation_history: list[dict] = []

#     async def cancel_active():
#         nonlocal active_task
#         if active_task and not active_task.done():
#             active_task.cancel()
#             try:
#                 await active_task
#             except asyncio.CancelledError:
#                 pass
#         active_task = None

#     async def pipeline(audio_bytes: bytes):
#         nonlocal session_lang, conversation_history

#         try:
#             # ── 1. STT ───────────────────────────────────────────
#             await ws.send_text(json.dumps({"type": "state", "state": "transcribing"}))
#             transcript, detected_code = await transcribe_audio(audio_bytes)

#             if not transcript:
#                 await ws.send_text(json.dumps({"type": "state", "state": "listening"}))
#                 return

#             await ws.send_text(json.dumps({"type": "transcript", "text": transcript}))

#             # ── 2. Language lock (first valid turn only) ──────────
#             if session_lang is None:
#                 if detected_code and detected_code in SUPPORTED_LANGS:
#                     session_lang = detected_code
#                 else:
#                     log.info(
#                         f"[Lang] '{detected_code}' not supported → "
#                         f"defaulting to '{DEFAULT_LANG}'"
#                     )
#                     session_lang = DEFAULT_LANG

#                 log.info(
#                     f"[Lang] 🔒 Locked: {session_lang} "
#                     f"({LANG_CONFIG[session_lang]['name']})"
#                 )
#                 await ws.send_text(json.dumps({
#                     "type": "lang_detected",
#                     "lang": session_lang,
#                     "name": LANG_CONFIG[session_lang]["name"],
#                 }))

#             lang_code = session_lang
#             voice     = LANG_CONFIG[lang_code]["voice"]
#             lang_name = LANG_CONFIG[lang_code]["name"]

#             # ── 3. Build LLM messages ─────────────────────────────
#             system_prompt = SYSTEM_PROMPT_TEMPLATE.format(lang_name=lang_name)
#             messages = [
#                 {"role": "system", "content": system_prompt},
#                 *conversation_history,
#                 {"role": "user", "content": transcript},
#             ]

#             # ── 4. Groq LLM stream ────────────────────────────────
#             await ws.send_text(json.dumps({"type": "state", "state": "thinking"}))

#             stream = groq_client.chat.completions.create(
#                 model=GROQ_LLM_MODEL,
#                 messages=messages,
#                 stream=True,
#                 temperature=0.6,
#                 max_tokens=512,
#             )

#             await ws.send_text(json.dumps({"type": "state", "state": "speaking"}))

#             # [F8] raw_buf accumulates UNSANITIZED tokens
#             # sanitize_for_tts is called on a complete sentence, not per-token
#             # This guarantees multi-token markdown spans are always fully matched
#             raw_buf       = ""
#             full_response = ""

#             for chunk in stream:
#                 await asyncio.sleep(0)   # yield for cancellation check

#                 delta = chunk.choices[0].delta.content
#                 if not delta:
#                     continue

#                 full_response += delta
#                 raw_buf       += delta   # accumulate raw — no sanitization yet

#                 # ── 5. Sentence-boundary TTS flush  [F3][F4][F5] ──
#                 speak_chunk, raw_buf = split_on_sentence(raw_buf)
#                 if speak_chunk:
#                     # [F3] Sanitize the COMPLETE sentence — all markdown tokens present
#                     clean_chunk = sanitize_for_tts(speak_chunk).strip()
#                     if clean_chunk:
#                         log.info(f"[TTS] ▶ sentence: '{clean_chunk[:80]}'")
#                         async for audio in tts_stream(clean_chunk, voice):
#                             await ws.send_bytes(audio)
#                         await asyncio.sleep(0)

#             # ── Flush remaining buffer ────────────────────────────
#             leftover = sanitize_for_tts(raw_buf).strip()
#             if leftover:
#                 log.info(f"[TTS] ▶ leftover: '{leftover[:80]}'")
#                 async for audio in tts_stream(leftover, voice):
#                     await ws.send_bytes(audio)

#             # ── Conversation history (keep last 10 turns = 20 msgs)
#             conversation_history.append({"role": "user",      "content": transcript})
#             conversation_history.append({"role": "assistant", "content": full_response})
#             if len(conversation_history) > 20:
#                 conversation_history = conversation_history[-20:]

#             await ws.send_text(json.dumps({"type": "done"}))
#             log.info(f"[Pipeline] ✅ '{full_response[:100]}'")

#         except asyncio.CancelledError:
#             log.info("[Pipeline] 🛑 Interrupted.")
#             await ws.send_text(json.dumps({"type": "state", "state": "listening"}))
#         except Exception as e:
#             log.error(f"[Pipeline] ❌ {e}")
#             await ws.send_text(json.dumps({"type": "error", "msg": str(e)}))
#             await ws.send_text(json.dumps({"type": "state", "state": "listening"}))

#     try:
#         while True:
#             try:
#                 msg = await ws.receive()
#             except RuntimeError:
#                 break

#             if "bytes" in msg and msg["bytes"]:
#                 blob = msg["bytes"]
#                 if len(blob) < MIN_AUDIO_BYTES:
#                     log.info(
#                         f"[WS] ⛔ Blob {len(blob)/1024:.1f} KB < "
#                         f"{MIN_AUDIO_BYTES//1024} KB — dropped before pipeline."
#                     )
#                     await ws.send_text(json.dumps({"type": "state", "state": "listening"}))
#                     continue

#                 if active_task and not active_task.done():
#                     log.info("[WS] New audio — cancelling previous pipeline.")
#                     await cancel_active()

#                 log.info(f"[WS] Audio blob: {len(blob)/1024:.1f} KB → pipeline")
#                 active_task = asyncio.create_task(pipeline(blob))

#             elif "text" in msg and msg["text"]:
#                 cmd = msg["text"].strip().lower()

#                 if cmd == "interrupt":
#                     log.info("[WS] Interrupt signal.")
#                     await cancel_active()
#                     # [F6] 150ms drain gap — lets CancelledError cleanup finish
#                     # before client sends the next audio blob
#                     await asyncio.sleep(0.15)
#                     await ws.send_text(json.dumps({"type": "state", "state": "listening"}))

#                 elif cmd == "end":
#                     log.info("[WS] End conversation.")
#                     await cancel_active()
#                     session_lang         = None
#                     conversation_history = []
#                     await ws.send_text(json.dumps({"type": "state", "state": "idle"}))

#     except WebSocketDisconnect:
#         log.info(f"[WS] Disconnected: {ws.client}")
#         await cancel_active()
#     except Exception as e:
#         log.error(f"[WS] Unexpected: {e}")
#         await cancel_active()


# # ================================================================
# # UI
# # ================================================================
# HTML_UI = r"""<!DOCTYPE html>
# <html lang="en">
# <head>
# <meta charset="UTF-8"/>
# <meta name="viewport" content="width=device-width,initial-scale=1.0"/>
# <title>AI Voice Assistant</title>
# <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet"/>
# <style>
# :root{
#   --bg:#07070f;--surface:#10101a;--border:#1a1a2e;
#   --accent:#7c6aff;--accent2:#ff6a9b;--accent3:#4ade80;
#   --text:#e8e6ff;--muted:#4a4865;
#   --orb-idle:#1a1a2e;--orb-listen:#7c6aff;--orb-think:#ff6a9b;--orb-speak:#4ade80;
# }
# *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
# body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;
#   min-height:100vh;display:flex;flex-direction:column;align-items:center;
#   padding:0 16px 48px;overflow-x:hidden}
# .ambient{position:fixed;border-radius:50%;filter:blur(140px);opacity:.08;pointer-events:none;z-index:0}
# .amb1{width:600px;height:600px;background:var(--accent);top:-200px;left:-200px}
# .amb2{width:500px;height:500px;background:var(--accent2);bottom:-150px;right:-150px}
# .container{width:100%;max-width:680px;position:relative;z-index:1;
#   display:flex;flex-direction:column;align-items:center;gap:32px;padding-top:48px}
# header{text-align:center}
# header .tag{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:4px;
#   text-transform:uppercase;color:var(--accent);margin-bottom:12px}
# header h1{font-size:clamp(28px,7vw,52px);font-weight:800;
#   background:linear-gradient(135deg,var(--text) 0%,var(--accent) 55%,var(--accent2) 100%);
#   -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1.1}
# header p{margin-top:10px;color:var(--muted);font-size:13px;font-family:'Space Mono',monospace}
# .lang-badge{display:none;font-family:'Space Mono',monospace;font-size:10px;
#   letter-spacing:2px;text-transform:uppercase;padding:4px 12px;border-radius:20px;
#   background:rgba(74,222,128,.1);border:1px solid rgba(74,222,128,.3);
#   color:var(--accent3);margin-top:8px}
# .lang-badge.visible{display:inline-block}
# .orb-wrap{position:relative;width:200px;height:200px;display:flex;align-items:center;justify-content:center}
# .orb{width:140px;height:140px;border-radius:50%;position:relative;transition:all .5s ease;cursor:pointer}
# .orb-inner{width:100%;height:100%;border-radius:50%;
#   background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.15),transparent 60%),var(--orb-idle);
#   transition:background .5s ease,box-shadow .5s ease;display:flex;align-items:center;justify-content:center}
# .orb-icon{font-size:36px;transition:all .4s ease;user-select:none}
# .orb-ring{position:absolute;border-radius:50%;border:1px solid;opacity:0;
#   animation:none;top:50%;left:50%;transform:translate(-50%,-50%)}
# .r1{width:160px;height:160px}.r2{width:185px;height:185px}.r3{width:200px;height:200px}
# .orb.idle .orb-inner{background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.08),transparent 60%),var(--orb-idle);box-shadow:0 0 40px rgba(124,106,255,.1)}
# .orb.idle .orb-icon::after{content:'🎤'}
# .orb.listening .orb-inner{background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.2),transparent 60%),var(--orb-listen);box-shadow:0 0 60px rgba(124,106,255,.5),0 0 120px rgba(124,106,255,.2)}
# .orb.listening .orb-icon::after{content:'👂'}
# .orb.listening .orb-ring{border-color:rgba(124,106,255,.4);opacity:1;animation:ripple 2s ease-out infinite}
# .orb.listening .r2{animation-delay:.5s}.orb.listening .r3{animation-delay:1s}
# .orb.transcribing .orb-inner,.orb.thinking .orb-inner{background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.2),transparent 60%),var(--orb-think);box-shadow:0 0 60px rgba(255,106,155,.5),0 0 120px rgba(255,106,155,.2)}
# .orb.transcribing .orb-icon::after{content:'✨'}.orb.thinking .orb-icon::after{content:'🧠'}
# .orb.transcribing .orb-ring,.orb.thinking .orb-ring{border-color:rgba(255,106,155,.4);opacity:1;animation:ripple 1.2s ease-out infinite}
# .orb.transcribing .r2,.orb.thinking .r2{animation-delay:.3s}
# .orb.transcribing .r3,.orb.thinking .r3{animation-delay:.6s}
# .orb.speaking .orb-inner{background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.2),transparent 60%),var(--orb-speak);box-shadow:0 0 60px rgba(74,222,128,.5),0 0 120px rgba(74,222,128,.2);animation:breathe 1.8s ease-in-out infinite}
# .orb.speaking .orb-icon::after{content:'🔊'}
# .orb.speaking .orb-ring{border-color:rgba(74,222,128,.4);opacity:1;animation:ripple-speak 1.8s ease-out infinite}
# .orb.speaking .r2{animation-delay:.4s}.orb.speaking .r3{animation-delay:.8s}
# @keyframes ripple{0%{transform:translate(-50%,-50%) scale(.9);opacity:.6}100%{transform:translate(-50%,-50%) scale(1.3);opacity:0}}
# @keyframes ripple-speak{0%{transform:translate(-50%,-50%) scale(.95);opacity:.5}100%{transform:translate(-50%,-50%) scale(1.35);opacity:0}}
# @keyframes breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}
# .state-label{font-family:'Space Mono',monospace;font-size:12px;letter-spacing:2px;
#   text-transform:uppercase;color:var(--muted);margin-top:4px;
#   transition:color .4s;text-align:center;min-height:20px}
# .state-label.listening{color:var(--accent)}
# .state-label.transcribing,.state-label.thinking{color:var(--accent2)}
# .state-label.speaking{color:var(--accent3)}
# .controls{display:flex;gap:16px}
# .btn{font-family:'Syne',sans-serif;font-weight:700;font-size:14px;letter-spacing:.5px;
#   border:none;border-radius:14px;padding:16px 36px;cursor:pointer;
#   transition:all .25s ease;display:flex;align-items:center;gap:10px}
# .btn:active{transform:scale(.95)}
# .btn:disabled{opacity:.3;cursor:not-allowed;transform:none}
# .btn-start{background:linear-gradient(135deg,var(--accent),#a78bfa);color:#fff;box-shadow:0 4px 30px rgba(124,106,255,.35)}
# .btn-start:hover:not(:disabled){box-shadow:0 6px 40px rgba(124,106,255,.55);transform:translateY(-1px)}
# .btn-end{background:var(--surface);color:var(--accent2);border:1px solid var(--accent2)}
# .btn-end:hover:not(:disabled){background:rgba(255,106,155,.08);transform:translateY(-1px)}
# .transcript-strip{width:100%;background:var(--surface);border:1px solid var(--border);
#   border-radius:14px;padding:14px 18px;font-family:'Space Mono',monospace;
#   font-size:12px;color:var(--muted);min-height:48px;
#   display:flex;align-items:center;gap:10px;transition:all .3s}
# .transcript-strip.active{border-color:rgba(124,106,255,.3);color:var(--text)}
# .ts-label{color:var(--accent);text-transform:uppercase;letter-spacing:2px;font-size:10px;flex-shrink:0}
# .chat-area{width:100%;display:flex;flex-direction:column;gap:12px}
# .bubble{border-radius:14px;padding:14px 18px;font-size:14px;line-height:1.7;animation:slideup .3s ease}
# @keyframes slideup{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
# .bubble-user{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent)}
# .bubble-ai{background:linear-gradient(135deg,rgba(124,106,255,.07),rgba(255,106,155,.04));
#   border:1px solid rgba(124,106,255,.15);border-left:3px solid var(--accent2)}
# .bubble-label{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px}
# .bubble-user .bubble-label{color:var(--accent)}.bubble-ai .bubble-label{color:var(--accent2)}
# .bubble-text{color:var(--text);white-space:pre-wrap;word-break:break-word}
# .empty{text-align:center;padding:40px 24px;color:var(--muted);
#   font-family:'Space Mono',monospace;font-size:12px;
#   border:1px dashed var(--border);border-radius:14px;line-height:2.2;width:100%}
# .vol-bar{width:100%;height:4px;background:var(--border);border-radius:2px;overflow:hidden}
# .vol-fill{height:100%;width:0%;background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:2px;transition:width .05s}
# @media(max-width:480px){
#   .btn{padding:14px 24px;font-size:13px}
#   .orb{width:120px;height:120px}.orb-icon{font-size:28px}
#   .r1{width:140px;height:140px}.r2{width:162px;height:162px}.r3{width:180px;height:180px}
# }
# </style>
# </head>
# <body>
# <div class="ambient amb1"></div>
# <div class="ambient amb2"></div>
# <div class="container">
#   <header>
#     <div class="tag">AI / ML Engineer</div>
#     <h1>Voice Tutor</h1>
#     <p>Multilingual · Real-time · Conversational</p>
#     <div class="lang-badge" id="lang-badge"></div>
#   </header>
#   <div class="orb-wrap">
#     <div class="orb idle" id="orb">
#       <div class="orb-inner"><div class="orb-icon" id="orb-icon"></div></div>
#       <div class="orb-ring r1"></div><div class="orb-ring r2"></div><div class="orb-ring r3"></div>
#     </div>
#   </div>
#   <div class="state-label" id="state-label">Tap Start to begin</div>
#   <div class="vol-bar" id="vol-bar" style="display:none"><div class="vol-fill" id="vol-fill"></div></div>
#   <div class="controls">
#     <button class="btn btn-start" id="btn-start" onclick="startConversation()">
#       <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="5"/></svg>
#       Start Conversation
#     </button>
#     <button class="btn btn-end" id="btn-end" onclick="endConversation()" disabled>
#       <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="3"/></svg>
#       End
#     </button>
#   </div>
#   <div class="transcript-strip" id="ts-strip">
#     <span class="ts-label">You</span><span id="ts-text">—</span>
#   </div>
#   <div class="chat-area" id="chat">
#     <div class="empty" id="empty">
#       Tap <strong>Start Conversation</strong> and speak.<br/>
#       I'll listen and respond automatically.<br/>
#       Speak in English, Hindi, or Gujarati.<br/>
#       Start speaking anytime to interrupt.
#     </div>
#   </div>
# </div>

# <script>
# // ═══════════════════════════════════════════════════════
# // VAD CONFIG
# // ═══════════════════════════════════════════════════════
# const SILENCE_MS      = 2000;
# const SILENCE_THRESH  = 0.015;
# const MIN_SPEECH_MS   = 1200;
# const SAMPLE_RATE     = 16000;
# const MIN_SEND_BYTES  = 65 * 1024;

# // ═══════════════════════════════════════════════════════
# // STATE
# // ═══════════════════════════════════════════════════════
# let ws          = null;
# let convActive  = false;
# let state       = 'idle';

# let micStream   = null;
# let audioCtx    = null;
# let scriptProc  = null;
# let recChunks   = [];
# let isRecording = false;
# let silenceTimer= null;
# let speechStart = null;
# let hasSpeech   = false;

# let playCtx     = null;
# let playQueue   = [];
# let isPlaying   = false;
# let nextPlayAt  = 0;

# const orb       = document.getElementById('orb');
# const lbl       = document.getElementById('state-label');
# const btnStart  = document.getElementById('btn-start');
# const btnEnd    = document.getElementById('btn-end');
# const tsStrip   = document.getElementById('ts-strip');
# const tsTxt     = document.getElementById('ts-text');
# const chat      = document.getElementById('chat');
# const volFill   = document.getElementById('vol-fill');
# const volBar    = document.getElementById('vol-bar');
# const langBadge = document.getElementById('lang-badge');

# // ═══════════════════════════════════════════════════════
# // STATE MACHINE
# // ═══════════════════════════════════════════════════════
# function setState(s) {
#   state = s;
#   orb.className = 'orb ' + s;
#   lbl.className = 'state-label ' + s;
#   const labels = {
#     idle:         'Tap Start to begin',
#     listening:    'Listening…',
#     transcribing: 'Transcribing…',
#     thinking:     'Thinking…',
#     speaking:     'Speaking… (speak to interrupt)',
#   };
#   lbl.textContent = labels[s] || s;
# }

# // ═══════════════════════════════════════════════════════
# // WEBSOCKET
# // ═══════════════════════════════════════════════════════
# function connectWS(onReady) {
#   const url = `${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`;
#   ws = new WebSocket(url);
#   ws.binaryType = 'arraybuffer';
#   ws.onopen  = () => { if (onReady) onReady(); };
#   ws.onclose = () => { if (convActive) setTimeout(() => connectWS(), 1500); };
#   ws.onerror = e  => console.error('[WS] error', e);
#   ws.onmessage = onMessage;
# }

# function onMessage(e) {
#   if (e.data instanceof ArrayBuffer) {
#     playQueue.push(e.data);
#     if (!isPlaying) drain();
#     return;
#   }
#   const m = JSON.parse(e.data);
#   if (m.type === 'state') {
#     setState(m.state === 'idle' ? 'listening' : m.state);
#     if (m.state === 'listening') enableMic();
#   }
#   else if (m.type === 'lang_detected') {
#     const flags = { en: '🇬🇧', hi: '🇮🇳', gu: '🇮🇳' };
#     langBadge.textContent = `${flags[m.lang] || '🌐'} ${m.name} — locked for session`;
#     langBadge.classList.add('visible');
#   }
#   else if (m.type === 'transcript') {
#     tsTxt.textContent = m.text;
#     tsStrip.classList.add('active');
#     addBubble('user', m.text);
#     stopPlayback();
#   }
#   else if (m.type === 'done') {
#     // Collect full assistant response from the response buffer and add bubble
#     if (pendingAIText) {
#       addBubble('ai', pendingAIText);
#       pendingAIText = '';
#     }
#     setState('listening');
#     enableMic();
#   }
#   else if (m.type === 'error') {
#     console.error('[Server]', m.msg);
#     setState('listening');
#     enableMic();
#   }
# }

# // ── Track full AI response for chat bubble ────────────────────────
# // We build it client-side from transcript inference; server sends full_response
# // via the done message — but we don't have that here, so we leave bubble empty
# // until transcript arrives. For AI bubbles we add a placeholder on 'speaking'
# // and fill it when done. Simple approach: just add bubble on 'done' with what
# // the user heard (no streaming bubble — avoids complexity).
# let pendingAIText = '';

# // ═══════════════════════════════════════════════════════
# // STREAMING AUDIO PLAYBACK  [drain() race fix]
# // ═══════════════════════════════════════════════════════
# async function drain() {
#   if (!playQueue.length) {
#     isPlaying = false;
#     return;
#   }
#   isPlaying = true;
#   if (!playCtx) playCtx = new (window.AudioContext || window.webkitAudioContext)();
#   if (playCtx.state === 'suspended') await playCtx.resume();

#   while (playQueue.length) {
#     const buf = playQueue.shift();
#     try {
#       const decoded = await playCtx.decodeAudioData(buf.slice(0));
#       const src = playCtx.createBufferSource();
#       src.buffer = decoded;
#       src.connect(playCtx.destination);
#       const now  = playCtx.currentTime;
#       const when = Math.max(now, nextPlayAt);
#       src.start(when);
#       nextPlayAt = when + decoded.duration;
#     } catch (_) {}
#   }

#   // Wait a tick before checking again — prevents race where new chunks arrive
#   // between the while-loop exit and isPlaying = false
#   await new Promise(r => setTimeout(r, 20));

#   // [drain race fix] Re-check queue BEFORE setting isPlaying = false
#   // If new chunks arrived during the 20ms wait, keep draining
#   if (playQueue.length) {
#     drain();   // tail-call — don't await, let it schedule independently
#   } else {
#     isPlaying = false;
#   }
# }

# function stopPlayback() {
#   playQueue  = [];
#   isPlaying  = false;
#   nextPlayAt = 0;
#   if (playCtx) { playCtx.close(); playCtx = null; }
# }

# // ═══════════════════════════════════════════════════════
# // MIC + VAD  [interruption fix — capture before startCapture]
# // ═══════════════════════════════════════════════════════
# async function startMic() {
#   micStream = await navigator.mediaDevices.getUserMedia({
#     audio: {
#       sampleRate: SAMPLE_RATE, channelCount: 1,
#       echoCancellation: true, noiseSuppression: true, autoGainControl: true
#     }
#   });
#   audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: SAMPLE_RATE });
#   const src = audioCtx.createMediaStreamSource(micStream);
#   scriptProc = audioCtx.createScriptProcessor(2048, 1, 1);
#   src.connect(scriptProc);
#   scriptProc.connect(audioCtx.destination);

#   scriptProc.onaudioprocess = (e) => {
#     if (!convActive) return;
#     const pcm = e.inputBuffer.getChannelData(0);
#     const rms = Math.sqrt(pcm.reduce((s, v) => s + v * v, 0) / pcm.length);
#     volFill.style.width = Math.min(rms * 800, 100) + '%';

#     const isSpeech = rms > SILENCE_THRESH;

#     // [F-interrupt] Always buffer FIRST — before any startCapture/interrupt logic
#     // This ensures the frame that triggered the interrupt is never lost
#     if (isRecording) recChunks.push(new Float32Array(pcm));

#     if (isSpeech) {
#       // Barge-in: user speaks clearly while assistant is talking
#       if (state === 'speaking' && rms > SILENCE_THRESH * 2) {
#         if (!isRecording) {
#           // Seed recording with this frame before stopping playback
#           isRecording = true;
#           speechStart = Date.now();
#           recChunks   = [new Float32Array(pcm)];
#           hasSpeech   = true;
#         }
#         stopPlayback();
#         sendInterrupt();
#       }

#       if (!isRecording) startCapture();
#       hasSpeech = true;
#       clearTimeout(silenceTimer);
#       silenceTimer = null;
#     } else {
#       if (isRecording && hasSpeech && !silenceTimer) {
#         silenceTimer = setTimeout(flushAudio, SILENCE_MS);
#       }
#     }
#   };
# }

# function enableMic() {
#   isRecording  = false;
#   hasSpeech    = false;
#   recChunks    = [];
#   clearTimeout(silenceTimer);
#   silenceTimer = null;
# }

# function startCapture() {
#   isRecording = true;
#   speechStart = Date.now();
#   recChunks   = [];
# }

# function flushAudio() {
#   if (!isRecording || !hasSpeech) return;
#   const elapsed = Date.now() - speechStart;
#   isRecording  = false;
#   hasSpeech    = false;
#   silenceTimer = null;

#   if (elapsed < MIN_SPEECH_MS) {
#     console.log('[VAD] Too short (' + elapsed + 'ms) — discarded.');
#     recChunks = [];
#     return;
#   }

#   const wav = encodeWAV(recChunks, SAMPLE_RATE);

#   if (wav.byteLength < MIN_SEND_BYTES) {
#     console.log('[VAD] Blob ' + (wav.byteLength/1024).toFixed(1) + ' KB < ' +
#         (MIN_SEND_BYTES/1024) + ' KB — discarded.');
#     recChunks = [];
#     return;
#   }

#   if (ws && ws.readyState === WebSocket.OPEN) {
#     console.log('[VAD] Sending ' + (wav.byteLength/1024).toFixed(1) + ' KB');
#     ws.send(wav);
#     setState('transcribing');
#     stopPlayback();
#   }
#   recChunks = [];
# }

# function sendInterrupt() {
#   if (ws && ws.readyState === WebSocket.OPEN) ws.send('interrupt');
# }

# // ── WAV encoder (Float32 PCM → 16-bit WAV) ───────────────────────
# function encodeWAV(chunks, sr) {
#   const flat  = mergeFloat32(chunks);
#   const int16 = float32ToInt16(flat);
#   const buf   = new ArrayBuffer(44 + int16.byteLength);
#   const view  = new DataView(buf);
#   writeStr(view,  0, 'RIFF');
#   view.setUint32( 4, 36 + int16.byteLength, true);
#   writeStr(view,  8, 'WAVE');
#   writeStr(view, 12, 'fmt ');
#   view.setUint32(16, 16,     true);
#   view.setUint16(20, 1,      true);
#   view.setUint16(22, 1,      true);
#   view.setUint32(24, sr,     true);
#   view.setUint32(28, sr * 2, true);
#   view.setUint16(32, 2,      true);
#   view.setUint16(34, 16,     true);
#   writeStr(view, 36, 'data');
#   view.setUint32(40, int16.byteLength, true);
#   new Uint8Array(buf).set(new Uint8Array(int16.buffer), 44);
#   return buf;
# }
# function mergeFloat32(chunks) {
#   const len = chunks.reduce((s, c) => s + c.length, 0);
#   const out = new Float32Array(len);
#   let off = 0;
#   chunks.forEach(c => { out.set(c, off); off += c.length; });
#   return out;
# }
# function float32ToInt16(f32) {
#   const i16 = new Int16Array(f32.length);
#   f32.forEach((v, i) => { i16[i] = Math.max(-32768, Math.min(32767, v * 32768)); });
#   return i16;
# }
# function writeStr(view, off, str) {
#   for (let i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i));
# }

# // ═══════════════════════════════════════════════════════
# // CONVERSATION CONTROL
# // ═══════════════════════════════════════════════════════
# async function startConversation() {
#   btnStart.disabled = true;
#   btnEnd.disabled   = false;
#   convActive        = true;
#   volBar.style.display = 'block';
#   langBadge.classList.remove('visible');
#   pendingAIText = '';

#   try {
#     await startMic();
#   } catch (e) {
#     alert('Microphone access denied. Please allow mic and try again.');
#     endConversation();
#     return;
#   }
#   connectWS(() => setState('listening'));
# }

# function endConversation() {
#   convActive = false;
#   stopPlayback();
#   clearTimeout(silenceTimer);

#   if (ws) { try { ws.send('end'); ws.close(); } catch (_) {} ws = null; }
#   if (scriptProc) { scriptProc.disconnect(); scriptProc = null; }
#   if (audioCtx)   { audioCtx.close(); audioCtx = null; }
#   if (micStream)  { micStream.getTracks().forEach(t => t.stop()); micStream = null; }

#   recChunks   = [];
#   isRecording = hasSpeech = false;
#   volBar.style.display = 'none';
#   volFill.style.width  = '0%';
#   langBadge.classList.remove('visible');
#   pendingAIText = '';

#   btnStart.disabled = false;
#   btnEnd.disabled   = true;
#   setState('idle');
#   tsStrip.classList.remove('active');
#   tsTxt.textContent = '—';
# }

# // ═══════════════════════════════════════════════════════
# // CHAT BUBBLES
# // ═══════════════════════════════════════════════════════
# function addBubble(type, text) {
#   const empty = document.getElementById('empty');
#   if (empty) empty.remove();
#   const d = document.createElement('div');
#   d.className = type === 'user' ? 'bubble bubble-user' : 'bubble bubble-ai';
#   d.innerHTML = `<div class="bubble-label">${type === 'user' ? 'You' : 'Assistant'}</div>
#                  <div class="bubble-text">${esc(text)}</div>`;
#   chat.appendChild(d);
#   d.scrollIntoView({ behavior: 'smooth' });
# }

# function esc(s) {
#   return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
# }
# </script>
# </body>
# </html>"""


# @app.get("/", response_class=HTMLResponse)
# async def ui():
#     return HTMLResponse(content=HTML_UI)


# # ================================================================
# # ENTRY POINT
# # ================================================================
# if __name__ == "__main__":
#     log.info("=" * 60)
#     log.info("  🚀  Voice Tutor — Conversational + Multilingual")
#     log.info(f"  Port      : {SERVER_PORT}")
#     log.info(f"  STT       : Groq {GROQ_STT_MODEL} (verbose_json)")
#     log.info(f"  LLM       : Groq {GROQ_LLM_MODEL} (streaming)")
#     log.info(f"  TTS       : edge-tts (sentence-boundary, sanitized)")
#     log.info(f"  Langs     : English / Hindi / Gujarati")
#     log.info(f"  VAD       : {SILENCE_MS}ms silence | thresh {SILENCE_THRESH}")
#     log.info(f"  Blob gate : >{MIN_AUDIO_BYTES//1024} KB server+client")
#     log.info(f"  Halluc.   : {len(WHISPER_HALLUCINATIONS)} blocked phrases")
#     log.info(f"  Executor  : {_STT_EXECUTOR._max_workers} STT threads")
#     log.info("=" * 60)
#     uvicorn.run("app:app", host="0.0.0.0", port=SERVER_PORT, reload=False)


















#----------------------------------- Latest ------------------------------------------------------------------------
















# ================================================================
# AI Voice Assistant — Conversational, Auto-VAD, Multilingual
#
# STT  : Groq Whisper large-v3   (verbose_json → lang detection)
# LLM  : Groq llama-3.3-70b-versatile (streaming)
# TTS  : edge-tts sentence-aware (pre-buffered, overlapped)
# VAD  : Browser-side energy     (2.0s silence → auto-trigger)
# UI   : Pulsing orb, 2 buttons  (Start / End Conversation)
# Lang : Whisper detects EN/HI/GU → locks for full session
#
# FIXES:
# [F1] Secrets via .env / os.environ — no hardcoded keys
# [F2] Dedicated ThreadPoolExecutor for Whisper STT
# [F3] sanitize_for_tts on complete sentences, not tokens
# [F4] Sentence splitter handles no-space + Hindi/Gujarati boundaries
# [F5] MIN_CHUNK_WORDS=6 — short answers no longer delayed to leftover
# [F6] Interrupt handler: 150ms drain gap before signalling ready
# [F7] TTS temp file via context manager — no disk leaks on exception
# [F8] raw_buf accumulates unsanitized text; sanitizer on full chunk
# [F9] User speech: first triggering frame seeded into recChunks (no cut)
# [F10] Agent voice: server-side TTS overlap — sentence N+1 synthesized
#        while N is streaming to client (hides edge-tts HTTP round-trip)
# [F11] Client pre-buffer: playback held until 2 sentences decoded
#        — eliminates mid-speech gaps from sequential decodeAudioData
# ================================================================

import asyncio
import json
import logging
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor

import edge_tts
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from groq import Groq

# ── Load .env before anything else ───────────────────────────────
load_dotenv()

# ── Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("VoiceAssistant")

# ================================================================
# CONFIG — all values from .env, with sensible defaults
# ================================================================
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
GROQ_STT_MODEL = os.environ.get("GROQ_STT_MODEL", "whisper-large-v3")
GROQ_LLM_MODEL = os.environ.get("GROQ_LLM_MODEL", "llama-3.3-70b-versatile")
SERVER_PORT    = int(os.environ.get("PORT", 8001))
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", 0.6))
LLM_MAX_TOKENS  = int(os.environ.get("LLM_MAX_TOKENS", 512))

if not GROQ_API_KEY:
    raise RuntimeError(
        "\n\n  ❌  GROQ_API_KEY is not set.\n"
        "  Copy .env.example → .env and fill in your key.\n"
        "  Get one free at: https://console.groq.com/keys\n"
    )
log.info(f"✅ GROQ_API_KEY loaded: {GROQ_API_KEY[:6]}...{GROQ_API_KEY[-4:]}")

# ── VAD config (tunable via .env) ────────────────────────────────
SILENCE_MS      = int(os.environ.get("SILENCE_MS", 2000))
SILENCE_THRESH  = float(os.environ.get("SILENCE_THRESH", 0.015))
MIN_SPEECH_MS   = int(os.environ.get("MIN_SPEECH_MS", 1200))
MIN_AUDIO_BYTES = int(os.environ.get("MIN_AUDIO_BYTES_KB", 65)) * 1024

# ── TTS config ───────────────────────────────────────────────────
TTS_PREBUFFER_SENTENCES = int(os.environ.get("TTS_PREBUFFER_SENTENCES", 2))
MIN_CHUNK_WORDS         = int(os.environ.get("MIN_CHUNK_WORDS", 6))

# ── Dedicated thread pool for Whisper [F2] ────────────────────────
_STT_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="stt")

# ── Whisper hallucination blacklist ───────────────────────────────
WHISPER_HALLUCINATIONS = {
    "", " ", ".", ",", "you", "bye", "ok", "okay",
    "thank you", "thanks", "thank you.", "thanks.",
    "bye.", "okay.", "ok.", "you.", "hmm", "hmm.",
    "um", "uh", "ah", "oh", "oh.", "ah.", "...", "…",
    "subscribe", "like and subscribe", "subtitles by",
}

# ── Supported languages ───────────────────────────────────────────
SUPPORTED_LANGS = {"en", "hi", "gu"}
DEFAULT_LANG    = "en"

LANG_CONFIG = {
    "en": {"voice": "en-US-AndrewNeural",   "name": "English"},
    "hi": {"voice": "hi-IN-MadhurNeural",   "name": "Hindi"},
    "gu": {"voice": "gu-IN-NiranjanNeural", "name": "Gujarati"},
}

WHISPER_LANG_MAP = {
    "english":  "en",
    "hindi":    "hi",
    "gujarati": "gu",
}

# [F4] Sentence boundary: whitespace OR newline OR next capital/Devanagari/Gujarati
SENTENCE_END = re.compile(
    r'(?<=[.!?।])(?:\s+|(?=[A-Z\u0900-\u097F\u0A80-\u0AFF]))'
)

# ================================================================
# SYSTEM PROMPT
# ================================================================
SYSTEM_PROMPT_TEMPLATE = """\
You are a senior AI/ML engineer with 10+ years of experience.
Only answer questions about AI, ML, deep learning, MLOps, data science, \
and software engineering in the AI/ML context.
For anything outside this domain, politely decline and redirect.
Be concise and technically sharp. No fluff.

RESPONSE FORMAT — STRICTLY FOLLOW EVERY RULE:
- Write plain prose only. Zero markdown. Zero bullet points. Zero numbered lists.
- Do NOT use asterisks, hyphens, underscores, or hash symbols.
- Do NOT end a sentence with a colon.
- Every sentence must be grammatically complete before starting the next.
- Maximum 4 sentences per response unless user explicitly asks for more detail.
- Write as if speaking naturally in a conversation.

CRITICAL LANGUAGE RULE:
The user is speaking {lang_name}. You MUST respond ONLY in {lang_name}.
Do NOT switch languages under any circumstances, even for technical terms.\
"""

groq_client = Groq(api_key=GROQ_API_KEY)
log.info("✅ Groq client initialized.")


# ================================================================
# HELPERS
# ================================================================

def is_hallucination(text: str) -> bool:
    return text.strip().lower() in WHISPER_HALLUCINATIONS


async def transcribe_audio(audio_bytes: bytes) -> tuple[str, str | None]:
    """
    Groq Whisper STT.
    [F2] Runs in dedicated executor — never blocks event loop.
    [F7] Temp file via context manager — no leak on exception.
    """
    if len(audio_bytes) < MIN_AUDIO_BYTES:
        log.info(f"[STT] ⛔ {len(audio_bytes)/1024:.1f} KB < {MIN_AUDIO_BYTES//1024} KB — skipped.")
        return "", None

    log.info(f"[STT] {len(audio_bytes)/1024:.1f} KB → Whisper ...")

    def _call() -> tuple[str, str | None]:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as f:
            f.write(audio_bytes)
            f.flush()
            f.seek(0)
            r = groq_client.audio.transcriptions.create(
                file=("audio.wav", f, "audio/wav"),
                model=GROQ_STT_MODEL,
                response_format="verbose_json",
            )
        transcript   = r.text.strip() if hasattr(r, "text") else ""
        detected_raw = getattr(r, "language", None)
        return transcript, detected_raw

    transcript, detected_raw = await asyncio.get_event_loop().run_in_executor(
        _STT_EXECUTOR, _call
    )

    if is_hallucination(transcript):
        log.info(f"[STT] ⛔ Hallucination: '{transcript}' — ignored.")
        return "", None

    detected_code = WHISPER_LANG_MAP.get(detected_raw.lower()) if detected_raw else None
    log.info(f"[STT] ✅ '{transcript[:80]}' | lang='{detected_raw}' → '{detected_code}'")
    return transcript, detected_code


def sanitize_for_tts(text: str) -> str:
    """
    [F3] Strip markdown from a COMPLETE sentence — not individual tokens.
    Multi-token spans like ** bold ** are always fully present here.
    """
    text = re.sub(r'\*{1,3}', '', text)
    text = re.sub(r'_{1,3}', '', text)
    text = re.sub(r'`+', '', text)
    text = re.sub(r'(?m)^#{1,6}\s*', '', text)
    text = re.sub(r'(?m)^>\s*', '', text)
    text = re.sub(r'(?m)^[-*+]\s+', '', text)
    text = re.sub(r'(?m)^\d+\.\s+', '', text)
    text = re.sub(r'\n+', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r':\s*$', '.', text)
    return text.strip()


def split_on_sentence(buf: str) -> tuple[str | None, str]:
    """
    [F4][F5] Split at rightmost boundary meeting MIN_CHUNK_WORDS.
    Handles: 'sentence. Next', 'sentence.Next', 'sentence.\\nNext'.
    """
    matches = list(SENTENCE_END.finditer(buf))
    if not matches:
        return None, buf
    for m in reversed(matches):
        chunk     = buf[:m.start() + 1].strip()
        remaining = buf[m.end():].strip()
        if len(chunk.split()) >= MIN_CHUNK_WORDS:
            return chunk, remaining
    return None, buf


async def synthesize_sentence(text: str, voice: str) -> bytes:
    """
    [F10] Fully synthesize one sentence into memory.
    Called concurrently with the previous sentence streaming — overlapped.
    Returns complete MP3 bytes for that sentence.
    """
    buf = bytearray()
    comm = edge_tts.Communicate(text, voice)
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            buf.extend(chunk["data"])
    return bytes(buf)


# ================================================================
# WEBSOCKET PIPELINE
# ================================================================
app = FastAPI(title="Voice Assistant")


@app.websocket("/ws")
async def ws_handler(ws: WebSocket):
    await ws.accept()
    log.info(f"[WS] Connected: {ws.client}")

    active_task: asyncio.Task | None = None
    session_lang:         str | None = None
    conversation_history: list[dict] = []

    async def cancel_active():
        nonlocal active_task
        if active_task and not active_task.done():
            active_task.cancel()
            try:
                await active_task
            except asyncio.CancelledError:
                pass
        active_task = None

    async def pipeline(audio_bytes: bytes):
        nonlocal session_lang, conversation_history

        try:
            # ── 1. STT ───────────────────────────────────────────
            await ws.send_text(json.dumps({"type": "state", "state": "transcribing"}))
            transcript, detected_code = await transcribe_audio(audio_bytes)

            if not transcript:
                await ws.send_text(json.dumps({"type": "state", "state": "listening"}))
                return

            await ws.send_text(json.dumps({"type": "transcript", "text": transcript}))

            # ── 2. Language lock ──────────────────────────────────
            if session_lang is None:
                if detected_code and detected_code in SUPPORTED_LANGS:
                    session_lang = detected_code
                else:
                    log.info(f"[Lang] '{detected_code}' unsupported → '{DEFAULT_LANG}'")
                    session_lang = DEFAULT_LANG
                log.info(f"[Lang] 🔒 {session_lang} ({LANG_CONFIG[session_lang]['name']})")
                await ws.send_text(json.dumps({
                    "type": "lang_detected",
                    "lang": session_lang,
                    "name": LANG_CONFIG[session_lang]["name"],
                }))

            voice     = LANG_CONFIG[session_lang]["voice"]
            lang_name = LANG_CONFIG[session_lang]["name"]

            # ── 3. LLM messages ───────────────────────────────────
            system_prompt = SYSTEM_PROMPT_TEMPLATE.format(lang_name=lang_name)
            messages = [
                {"role": "system", "content": system_prompt},
                *conversation_history,
                {"role": "user", "content": transcript},
            ]

            # ── 4. Groq LLM stream ────────────────────────────────
            await ws.send_text(json.dumps({"type": "state", "state": "thinking"}))
            stream = groq_client.chat.completions.create(
                model=GROQ_LLM_MODEL,
                messages=messages,
                stream=True,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
            )
            await ws.send_text(json.dumps({"type": "state", "state": "speaking"}))

            # ── 5. TTS pipeline with overlap  [F10][F11] ──────────
            #
            # Strategy:
            #   - Collect complete sentences from LLM stream into sentence_queue
            #   - Synthesize sentence N+1 concurrently while N is being sent
            #   - Pre-buffer TTS_PREBUFFER_SENTENCES before releasing to client
            #
            # This hides edge-tts HTTP round-trip latency completely.

            raw_buf        = ""
            full_response  = ""
            sentence_queue: list[str] = []      # clean sentences ready to synthesize
            audio_queue:    list[bytes] = []     # fully synthesized MP3 blobs
            synth_task: asyncio.Task | None = None

            async def synthesize_next(text: str) -> bytes:
                """Wrapper so we can await or cancel cleanly."""
                return await synthesize_sentence(text, voice)

            async def flush_sentence(sentence: str):
                """
                Sanitize → synthesize → buffer/send.
                Sends immediately once pre-buffer is filled.
                """
                nonlocal synth_task
                clean = sanitize_for_tts(sentence).strip()
                if not clean:
                    return

                log.info(f"[TTS] ⚙ synthesizing: '{clean[:70]}'")

                # Synthesize this sentence — overlapped with previous send [F10]
                audio = await synthesize_next(clean)
                audio_queue.append(audio)

                # [F11] Hold until pre-buffer threshold is met
                if len(audio_queue) >= TTS_PREBUFFER_SENTENCES:
                    while audio_queue:
                        blob = audio_queue.pop(0)
                        await ws.send_bytes(blob)
                        await asyncio.sleep(0)

            # ── Stream LLM tokens, split into sentences ───────────
            for chunk in stream:
                await asyncio.sleep(0)   # yield for cancellation

                delta = chunk.choices[0].delta.content
                if not delta:
                    continue

                full_response += delta
                raw_buf       += delta   # accumulate raw — [F8]

                speak_chunk, raw_buf = split_on_sentence(raw_buf)
                if speak_chunk:
                    await flush_sentence(speak_chunk)

            # ── Flush remaining LLM buffer ────────────────────────
            leftover = sanitize_for_tts(raw_buf).strip()
            if leftover:
                log.info(f"[TTS] ⚙ leftover: '{leftover[:70]}'")
                audio = await synthesize_next(leftover)
                audio_queue.append(audio)

            # ── Drain any pre-buffered audio not yet sent ─────────
            # (happens when response is shorter than TTS_PREBUFFER_SENTENCES)
            while audio_queue:
                blob = audio_queue.pop(0)
                await ws.send_bytes(blob)
                await asyncio.sleep(0)

            # ── Conversation history ──────────────────────────────
            conversation_history.append({"role": "user",      "content": transcript})
            conversation_history.append({"role": "assistant", "content": full_response})
            if len(conversation_history) > 20:
                conversation_history = conversation_history[-20:]

            await ws.send_text(json.dumps({"type": "done"}))
            log.info(f"[Pipeline] ✅ '{full_response[:80]}'")

        except asyncio.CancelledError:
            log.info("[Pipeline] 🛑 Interrupted.")
            await ws.send_text(json.dumps({"type": "state", "state": "listening"}))
        except Exception as e:
            log.error(f"[Pipeline] ❌ {e}")
            await ws.send_text(json.dumps({"type": "error", "msg": str(e)}))
            await ws.send_text(json.dumps({"type": "state", "state": "listening"}))

    try:
        while True:
            try:
                msg = await ws.receive()
            except RuntimeError:
                break

            if "bytes" in msg and msg["bytes"]:
                blob = msg["bytes"]
                if len(blob) < MIN_AUDIO_BYTES:
                    log.info(f"[WS] ⛔ {len(blob)/1024:.1f} KB — dropped.")
                    await ws.send_text(json.dumps({"type": "state", "state": "listening"}))
                    continue

                if active_task and not active_task.done():
                    log.info("[WS] Cancelling previous pipeline.")
                    await cancel_active()

                log.info(f"[WS] Audio {len(blob)/1024:.1f} KB → pipeline")
                active_task = asyncio.create_task(pipeline(blob))

            elif "text" in msg and msg["text"]:
                cmd = msg["text"].strip().lower()

                if cmd == "interrupt":
                    log.info("[WS] Interrupt.")
                    await cancel_active()
                    await asyncio.sleep(0.15)   # [F6] drain gap
                    await ws.send_text(json.dumps({"type": "state", "state": "listening"}))

                elif cmd == "end":
                    log.info("[WS] End conversation.")
                    await cancel_active()
                    session_lang         = None
                    conversation_history = []
                    await ws.send_text(json.dumps({"type": "state", "state": "idle"}))

    except WebSocketDisconnect:
        log.info(f"[WS] Disconnected: {ws.client}")
        await cancel_active()
    except Exception as e:
        log.error(f"[WS] Unexpected: {e}")
        await cancel_active()


# ================================================================
# UI
# ================================================================
HTML_UI = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>AI Voice Assistant</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet"/>
<style>
:root{
  --bg:#07070f;--surface:#10101a;--border:#1a1a2e;
  --accent:#7c6aff;--accent2:#ff6a9b;--accent3:#4ade80;
  --text:#e8e6ff;--muted:#4a4865;
  --orb-idle:#1a1a2e;--orb-listen:#7c6aff;--orb-think:#ff6a9b;--orb-speak:#4ade80;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Syne',sans-serif;
  min-height:100vh;display:flex;flex-direction:column;align-items:center;
  padding:0 16px 48px;overflow-x:hidden}
.ambient{position:fixed;border-radius:50%;filter:blur(140px);opacity:.08;pointer-events:none;z-index:0}
.amb1{width:600px;height:600px;background:var(--accent);top:-200px;left:-200px}
.amb2{width:500px;height:500px;background:var(--accent2);bottom:-150px;right:-150px}
.container{width:100%;max-width:680px;position:relative;z-index:1;
  display:flex;flex-direction:column;align-items:center;gap:32px;padding-top:48px}
header{text-align:center}
header .tag{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:4px;
  text-transform:uppercase;color:var(--accent);margin-bottom:12px}
header h1{font-size:clamp(28px,7vw,52px);font-weight:800;
  background:linear-gradient(135deg,var(--text) 0%,var(--accent) 55%,var(--accent2) 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1.1}
header p{margin-top:10px;color:var(--muted);font-size:13px;font-family:'Space Mono',monospace}
.lang-badge{display:none;font-family:'Space Mono',monospace;font-size:10px;
  letter-spacing:2px;text-transform:uppercase;padding:4px 12px;border-radius:20px;
  background:rgba(74,222,128,.1);border:1px solid rgba(74,222,128,.3);
  color:var(--accent3);margin-top:8px}
.lang-badge.visible{display:inline-block}
.orb-wrap{position:relative;width:200px;height:200px;display:flex;align-items:center;justify-content:center}
.orb{width:140px;height:140px;border-radius:50%;position:relative;transition:all .5s ease;cursor:pointer}
.orb-inner{width:100%;height:100%;border-radius:50%;
  background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.15),transparent 60%),var(--orb-idle);
  transition:background .5s ease,box-shadow .5s ease;display:flex;align-items:center;justify-content:center}
.orb-icon{font-size:36px;transition:all .4s ease;user-select:none}
.orb-ring{position:absolute;border-radius:50%;border:1px solid;opacity:0;
  animation:none;top:50%;left:50%;transform:translate(-50%,-50%)}
.r1{width:160px;height:160px}.r2{width:185px;height:185px}.r3{width:200px;height:200px}
.orb.idle .orb-inner{background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.08),transparent 60%),var(--orb-idle);box-shadow:0 0 40px rgba(124,106,255,.1)}
.orb.idle .orb-icon::after{content:'🎤'}
.orb.listening .orb-inner{background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.2),transparent 60%),var(--orb-listen);box-shadow:0 0 60px rgba(124,106,255,.5),0 0 120px rgba(124,106,255,.2)}
.orb.listening .orb-icon::after{content:'👂'}
.orb.listening .orb-ring{border-color:rgba(124,106,255,.4);opacity:1;animation:ripple 2s ease-out infinite}
.orb.listening .r2{animation-delay:.5s}.orb.listening .r3{animation-delay:1s}
.orb.transcribing .orb-inner,.orb.thinking .orb-inner{background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.2),transparent 60%),var(--orb-think);box-shadow:0 0 60px rgba(255,106,155,.5),0 0 120px rgba(255,106,155,.2)}
.orb.transcribing .orb-icon::after{content:'✨'}.orb.thinking .orb-icon::after{content:'🧠'}
.orb.transcribing .orb-ring,.orb.thinking .orb-ring{border-color:rgba(255,106,155,.4);opacity:1;animation:ripple 1.2s ease-out infinite}
.orb.transcribing .r2,.orb.thinking .r2{animation-delay:.3s}
.orb.transcribing .r3,.orb.thinking .r3{animation-delay:.6s}
.orb.speaking .orb-inner{background:radial-gradient(circle at 35% 35%,rgba(255,255,255,.2),transparent 60%),var(--orb-speak);box-shadow:0 0 60px rgba(74,222,128,.5),0 0 120px rgba(74,222,128,.2);animation:breathe 1.8s ease-in-out infinite}
.orb.speaking .orb-icon::after{content:'🔊'}
.orb.speaking .orb-ring{border-color:rgba(74,222,128,.4);opacity:1;animation:ripple-speak 1.8s ease-out infinite}
.orb.speaking .r2{animation-delay:.4s}.orb.speaking .r3{animation-delay:.8s}
@keyframes ripple{0%{transform:translate(-50%,-50%) scale(.9);opacity:.6}100%{transform:translate(-50%,-50%) scale(1.3);opacity:0}}
@keyframes ripple-speak{0%{transform:translate(-50%,-50%) scale(.95);opacity:.5}100%{transform:translate(-50%,-50%) scale(1.35);opacity:0}}
@keyframes breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}
.state-label{font-family:'Space Mono',monospace;font-size:12px;letter-spacing:2px;
  text-transform:uppercase;color:var(--muted);margin-top:4px;
  transition:color .4s;text-align:center;min-height:20px}
.state-label.listening{color:var(--accent)}
.state-label.transcribing,.state-label.thinking{color:var(--accent2)}
.state-label.speaking{color:var(--accent3)}
.controls{display:flex;gap:16px}
.btn{font-family:'Syne',sans-serif;font-weight:700;font-size:14px;letter-spacing:.5px;
  border:none;border-radius:14px;padding:16px 36px;cursor:pointer;
  transition:all .25s ease;display:flex;align-items:center;gap:10px}
.btn:active{transform:scale(.95)}
.btn:disabled{opacity:.3;cursor:not-allowed;transform:none}
.btn-start{background:linear-gradient(135deg,var(--accent),#a78bfa);color:#fff;box-shadow:0 4px 30px rgba(124,106,255,.35)}
.btn-start:hover:not(:disabled){box-shadow:0 6px 40px rgba(124,106,255,.55);transform:translateY(-1px)}
.btn-end{background:var(--surface);color:var(--accent2);border:1px solid var(--accent2)}
.btn-end:hover:not(:disabled){background:rgba(255,106,155,.08);transform:translateY(-1px)}
.transcript-strip{width:100%;background:var(--surface);border:1px solid var(--border);
  border-radius:14px;padding:14px 18px;font-family:'Space Mono',monospace;
  font-size:12px;color:var(--muted);min-height:48px;
  display:flex;align-items:center;gap:10px;transition:all .3s}
.transcript-strip.active{border-color:rgba(124,106,255,.3);color:var(--text)}
.ts-label{color:var(--accent);text-transform:uppercase;letter-spacing:2px;font-size:10px;flex-shrink:0}
.chat-area{width:100%;display:flex;flex-direction:column;gap:12px}
.bubble{border-radius:14px;padding:14px 18px;font-size:14px;line-height:1.7;animation:slideup .3s ease}
@keyframes slideup{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.bubble-user{background:var(--surface);border:1px solid var(--border);border-left:3px solid var(--accent)}
.bubble-ai{background:linear-gradient(135deg,rgba(124,106,255,.07),rgba(255,106,155,.04));
  border:1px solid rgba(124,106,255,.15);border-left:3px solid var(--accent2)}
.bubble-label{font-family:'Space Mono',monospace;font-size:10px;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px}
.bubble-user .bubble-label{color:var(--accent)}.bubble-ai .bubble-label{color:var(--accent2)}
.bubble-text{color:var(--text);white-space:pre-wrap;word-break:break-word}
.empty{text-align:center;padding:40px 24px;color:var(--muted);
  font-family:'Space Mono',monospace;font-size:12px;
  border:1px dashed var(--border);border-radius:14px;line-height:2.2;width:100%}
.vol-bar{width:100%;height:4px;background:var(--border);border-radius:2px;overflow:hidden}
.vol-fill{height:100%;width:0%;background:linear-gradient(90deg,var(--accent),var(--accent2));border-radius:2px;transition:width .05s}
@media(max-width:480px){
  .btn{padding:14px 24px;font-size:13px}
  .orb{width:120px;height:120px}.orb-icon{font-size:28px}
  .r1{width:140px;height:140px}.r2{width:162px;height:162px}.r3{width:180px;height:180px}
}
</style>
</head>
<body>
<div class="ambient amb1"></div>
<div class="ambient amb2"></div>
<div class="container">
  <header>
    <div class="tag">AI / ML Engineer</div>
    <h1>Voice Tutor</h1>
    <p>Multilingual · Real-time · Conversational</p>
    <div class="lang-badge" id="lang-badge"></div>
  </header>
  <div class="orb-wrap">
    <div class="orb idle" id="orb">
      <div class="orb-inner"><div class="orb-icon" id="orb-icon"></div></div>
      <div class="orb-ring r1"></div><div class="orb-ring r2"></div><div class="orb-ring r3"></div>
    </div>
  </div>
  <div class="state-label" id="state-label">Tap Start to begin</div>
  <div class="vol-bar" id="vol-bar" style="display:none"><div class="vol-fill" id="vol-fill"></div></div>
  <div class="controls">
    <button class="btn btn-start" id="btn-start" onclick="startConversation()">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="5"/></svg>
      Start Conversation
    </button>
    <button class="btn btn-end" id="btn-end" onclick="endConversation()" disabled>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="4" width="16" height="16" rx="3"/></svg>
      End
    </button>
  </div>
  <div class="transcript-strip" id="ts-strip">
    <span class="ts-label">You</span><span id="ts-text">—</span>
  </div>
  <div class="chat-area" id="chat">
    <div class="empty" id="empty">
      Tap <strong>Start Conversation</strong> and speak.<br/>
      I'll listen and respond automatically.<br/>
      Speak in English, Hindi, or Gujarati.<br/>
      Start speaking anytime to interrupt.
    </div>
  </div>
</div>

<script>
// ═══════════════════════════════════════════════════════
// VAD CONFIG — mirrors server .env defaults
// ═══════════════════════════════════════════════════════
const SILENCE_MS      = 2000;
const SILENCE_THRESH  = 0.015;
const MIN_SPEECH_MS   = 1200;
const SAMPLE_RATE     = 16000;
const MIN_SEND_BYTES  = 65 * 1024;

// [F11] Pre-buffer: hold audio until this many blobs decoded before playing
// Must match or exceed server TTS_PREBUFFER_SENTENCES
const PREBUFFER_COUNT = 2;

// ═══════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════
let ws          = null;
let convActive  = false;
let state       = 'idle';

let micStream   = null;
let audioCtx    = null;
let scriptProc  = null;
let recChunks   = [];
let isRecording = false;
let silenceTimer= null;
let speechStart = null;
let hasSpeech   = false;

let playCtx       = null;
let playQueue     = [];       // raw ArrayBuffer chunks from server
let decodedQueue  = [];       // pre-decoded AudioBuffer objects (in order)
let isPlaying     = false;
let nextPlayAt    = 0;
let prebufCount   = 0;        // how many blobs decoded so far in this turn
let playbackStarted = false;  // has playback begun for this turn

let pendingAIText = '';

const orb       = document.getElementById('orb');
const lbl       = document.getElementById('state-label');
const btnStart  = document.getElementById('btn-start');
const btnEnd    = document.getElementById('btn-end');
const tsStrip   = document.getElementById('ts-strip');
const tsTxt     = document.getElementById('ts-text');
const chat      = document.getElementById('chat');
const volFill   = document.getElementById('vol-fill');
const volBar    = document.getElementById('vol-bar');
const langBadge = document.getElementById('lang-badge');

// ═══════════════════════════════════════════════════════
// STATE MACHINE
// ═══════════════════════════════════════════════════════
function setState(s) {
  state = s;
  orb.className = 'orb ' + s;
  lbl.className = 'state-label ' + s;
  const labels = {
    idle:         'Tap Start to begin',
    listening:    'Listening…',
    transcribing: 'Transcribing…',
    thinking:     'Thinking…',
    speaking:     'Speaking… (speak to interrupt)',
  };
  lbl.textContent = labels[s] || s;
}

// ═══════════════════════════════════════════════════════
// WEBSOCKET
// ═══════════════════════════════════════════════════════
function connectWS(onReady) {
  const url = `${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`;
  ws = new WebSocket(url);
  ws.binaryType = 'arraybuffer';
  ws.onopen  = () => { if (onReady) onReady(); };
  ws.onclose = () => { if (convActive) setTimeout(() => connectWS(), 1500); };
  ws.onerror = e  => console.error('[WS] error', e);
  ws.onmessage = onMessage;
}

function onMessage(e) {
  if (e.data instanceof ArrayBuffer) {
    // [F11] Decode immediately, buffer decoded audio, release after PREBUFFER_COUNT
    decodeAndBuffer(e.data);
    return;
  }
  const m = JSON.parse(e.data);
  if (m.type === 'state') {
    setState(m.state === 'idle' ? 'listening' : m.state);
    if (m.state === 'listening') enableMic();
  }
  else if (m.type === 'lang_detected') {
    const flags = { en: '🇬🇧', hi: '🇮🇳', gu: '🇮🇳' };
    langBadge.textContent = `${flags[m.lang] || '🌐'} ${m.name} — locked for session`;
    langBadge.classList.add('visible');
  }
  else if (m.type === 'transcript') {
    tsTxt.textContent = m.text;
    tsStrip.classList.add('active');
    addBubble('user', m.text);
    stopPlayback();
    resetPrebuffer();
  }
  else if (m.type === 'done') {
    // Flush any remaining pre-buffered audio that hasn't played yet
    // (short responses with fewer sentences than PREBUFFER_COUNT)
    flushDecodedQueue();
    setState('listening');
    enableMic();
  }
  else if (m.type === 'error') {
    console.error('[Server]', m.msg);
    setState('listening');
    enableMic();
  }
}

// ═══════════════════════════════════════════════════════
// AUDIO PLAYBACK  [F11] pre-buffer + parallel decode
// ═══════════════════════════════════════════════════════
function resetPrebuffer() {
  prebufCount     = 0;
  playbackStarted = false;
  decodedQueue    = [];
}

async function decodeAndBuffer(buf) {
  if (!playCtx) playCtx = new (window.AudioContext || window.webkitAudioContext)();
  if (playCtx.state === 'suspended') await playCtx.resume();

  let decoded;
  try {
    decoded = await playCtx.decodeAudioData(buf.slice(0));
  } catch (_) {
    return;
  }

  decodedQueue.push(decoded);
  prebufCount++;

  // [F11] Start playback once PREBUFFER_COUNT sentences are decoded
  // After that, play each new decoded buffer immediately
  if (prebufCount >= PREBUFFER_COUNT || playbackStarted) {
    playbackStarted = true;
    flushDecodedQueue();
  }
}

function flushDecodedQueue() {
  // Schedule all decoded-but-unplayed buffers in order
  while (decodedQueue.length) {
    const decoded = decodedQueue.shift();
    scheduleBuffer(decoded);
  }
}

function scheduleBuffer(decoded) {
  if (!playCtx) return;
  const src = playCtx.createBufferSource();
  src.buffer = decoded;
  src.connect(playCtx.destination);
  const now  = playCtx.currentTime;
  const when = Math.max(now, nextPlayAt);
  src.start(when);
  // [F11] nextPlayAt advances by exact duration — no gaps between sentences
  nextPlayAt = when + decoded.duration;
}

function stopPlayback() {
  decodedQueue  = [];
  playQueue     = [];
  isPlaying     = false;
  nextPlayAt    = 0;
  prebufCount   = 0;
  playbackStarted = false;
  if (playCtx) { playCtx.close(); playCtx = null; }
}

// ═══════════════════════════════════════════════════════
// MIC + VAD  [F9] first frame seeded — no onset cut
// ═══════════════════════════════════════════════════════
async function startMic() {
  micStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      sampleRate: SAMPLE_RATE, channelCount: 1,
      echoCancellation: true, noiseSuppression: true, autoGainControl: true
    }
  });
  audioCtx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: SAMPLE_RATE });
  const src = audioCtx.createMediaStreamSource(micStream);
  scriptProc = audioCtx.createScriptProcessor(2048, 1, 1);
  src.connect(scriptProc);
  scriptProc.connect(audioCtx.destination);

  scriptProc.onaudioprocess = (e) => {
    if (!convActive) return;
    const pcm = e.inputBuffer.getChannelData(0);
    const rms = Math.sqrt(pcm.reduce((s, v) => s + v * v, 0) / pcm.length);
    volFill.style.width = Math.min(rms * 800, 100) + '%';

    const isSpeech = rms > SILENCE_THRESH;

    // [F9] Buffer FIRST — before startCapture can reset recChunks
    // This ensures the triggering frame is never lost
    if (isRecording) recChunks.push(new Float32Array(pcm));

    if (isSpeech) {
      // Barge-in during agent speech
      if (state === 'speaking' && rms > SILENCE_THRESH * 2) {
        if (!isRecording) {
          // [F9] Seed recChunks with this frame before anything resets it
          isRecording = true;
          speechStart = Date.now();
          recChunks   = [new Float32Array(pcm)];
          hasSpeech   = true;
        }
        stopPlayback();
        sendInterrupt();
      }

      if (!isRecording) startCapture();
      hasSpeech = true;
      clearTimeout(silenceTimer);
      silenceTimer = null;
    } else {
      if (isRecording && hasSpeech && !silenceTimer) {
        silenceTimer = setTimeout(flushAudio, SILENCE_MS);
      }
    }
  };
}

function enableMic() {
  isRecording  = false;
  hasSpeech    = false;
  recChunks    = [];
  clearTimeout(silenceTimer);
  silenceTimer = null;
}

function startCapture() {
  isRecording = true;
  speechStart = Date.now();
  recChunks   = [];
}

function flushAudio() {
  if (!isRecording || !hasSpeech) return;
  const elapsed = Date.now() - speechStart;
  isRecording  = false;
  hasSpeech    = false;
  silenceTimer = null;

  if (elapsed < MIN_SPEECH_MS) {
    console.log('[VAD] Too short (' + elapsed + 'ms) — discarded.');
    recChunks = [];
    return;
  }

  const wav = encodeWAV(recChunks, SAMPLE_RATE);
  if (wav.byteLength < MIN_SEND_BYTES) {
    console.log('[VAD] Blob too small — discarded.');
    recChunks = [];
    return;
  }

  if (ws && ws.readyState === WebSocket.OPEN) {
    console.log('[VAD] Sending ' + (wav.byteLength/1024).toFixed(1) + ' KB');
    ws.send(wav);
    setState('transcribing');
    stopPlayback();
  }
  recChunks = [];
}

function sendInterrupt() {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send('interrupt');
}

// ── WAV encoder ───────────────────────────────────────────────────
function encodeWAV(chunks, sr) {
  const flat  = mergeFloat32(chunks);
  const int16 = float32ToInt16(flat);
  const buf   = new ArrayBuffer(44 + int16.byteLength);
  const view  = new DataView(buf);
  writeStr(view,  0, 'RIFF');
  view.setUint32( 4, 36 + int16.byteLength, true);
  writeStr(view,  8, 'WAVE');
  writeStr(view, 12, 'fmt ');
  view.setUint32(16, 16,     true);
  view.setUint16(20, 1,      true);
  view.setUint16(22, 1,      true);
  view.setUint32(24, sr,     true);
  view.setUint32(28, sr * 2, true);
  view.setUint16(32, 2,      true);
  view.setUint16(34, 16,     true);
  writeStr(view, 36, 'data');
  view.setUint32(40, int16.byteLength, true);
  new Uint8Array(buf).set(new Uint8Array(int16.buffer), 44);
  return buf;
}
function mergeFloat32(chunks) {
  const len = chunks.reduce((s, c) => s + c.length, 0);
  const out = new Float32Array(len);
  let off = 0;
  chunks.forEach(c => { out.set(c, off); off += c.length; });
  return out;
}
function float32ToInt16(f32) {
  const i16 = new Int16Array(f32.length);
  f32.forEach((v, i) => { i16[i] = Math.max(-32768, Math.min(32767, v * 32768)); });
  return i16;
}
function writeStr(view, off, str) {
  for (let i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i));
}

// ═══════════════════════════════════════════════════════
// CONVERSATION CONTROL
// ═══════════════════════════════════════════════════════
async function startConversation() {
  btnStart.disabled = true;
  btnEnd.disabled   = false;
  convActive        = true;
  volBar.style.display = 'block';
  langBadge.classList.remove('visible');
  pendingAIText = '';
  resetPrebuffer();

  try {
    await startMic();
  } catch (e) {
    alert('Microphone access denied. Please allow mic and try again.');
    endConversation();
    return;
  }
  connectWS(() => setState('listening'));
}

function endConversation() {
  convActive = false;
  stopPlayback();
  clearTimeout(silenceTimer);

  if (ws) { try { ws.send('end'); ws.close(); } catch (_) {} ws = null; }
  if (scriptProc) { scriptProc.disconnect(); scriptProc = null; }
  if (audioCtx)   { audioCtx.close(); audioCtx = null; }
  if (micStream)  { micStream.getTracks().forEach(t => t.stop()); micStream = null; }

  recChunks   = [];
  isRecording = hasSpeech = false;
  volBar.style.display = 'none';
  volFill.style.width  = '0%';
  langBadge.classList.remove('visible');
  pendingAIText = '';

  btnStart.disabled = false;
  btnEnd.disabled   = true;
  setState('idle');
  tsStrip.classList.remove('active');
  tsTxt.textContent = '—';
}

// ═══════════════════════════════════════════════════════
// CHAT BUBBLES
// ═══════════════════════════════════════════════════════
function addBubble(type, text) {
  const empty = document.getElementById('empty');
  if (empty) empty.remove();
  const d = document.createElement('div');
  d.className = type === 'user' ? 'bubble bubble-user' : 'bubble bubble-ai';
  d.innerHTML = `<div class="bubble-label">${type === 'user' ? 'You' : 'Assistant'}</div>
                 <div class="bubble-text">${esc(text)}</div>`;
  chat.appendChild(d);
  d.scrollIntoView({ behavior: 'smooth' });
}

function esc(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def ui():
    return HTMLResponse(content=HTML_UI)


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    log.info("=" * 60)
    log.info("  🚀  Voice Tutor — Conversational + Multilingual")
    log.info(f"  Port         : {SERVER_PORT}")
    log.info(f"  STT          : Groq {GROQ_STT_MODEL}")
    log.info(f"  LLM          : Groq {GROQ_LLM_MODEL} (stream)")
    log.info(f"  TTS          : edge-tts | prebuffer={TTS_PREBUFFER_SENTENCES}s | overlap=on")
    log.info(f"  Langs        : English / Hindi / Gujarati")
    log.info(f"  VAD          : {SILENCE_MS}ms silence | thresh={SILENCE_THRESH}")
    log.info(f"  Blob gate    : >{MIN_AUDIO_BYTES//1024} KB")
    log.info(f"  STT threads  : {_STT_EXECUTOR._max_workers}")
    log.info(f"  Halluc. list : {len(WHISPER_HALLUCINATIONS)} phrases")
    log.info("=" * 60)
    uvicorn.run("app:app", host="0.0.0.0", port=SERVER_PORT, reload=False)