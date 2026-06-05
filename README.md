# 🎙️ AI Voice Tutor

A real-time multilingual AI voice assistant built with FastAPI, Groq, Edge-TTS, and WebSockets.

The assistant listens to the user through the browser microphone, automatically detects when the user has finished speaking, transcribes speech using Groq Whisper, generates responses using Llama 3.3 70B, and speaks the response back using Microsoft Edge TTS.

Supported languages include English, Hindi, and Gujarati with automatic language detection and session language locking.

---

## ✨ Features

### Speech-to-Text

* Groq Whisper Large-v3
* Automatic language detection
* Hallucination filtering
* Dedicated thread pool for transcription
* Supports English, Hindi, and Gujarati

### Language Model

* Groq Llama 3.3 70B Versatile
* Streaming responses
* Conversation memory
* AI/ML-focused assistant behavior
* Language-locked responses

### Text-to-Speech

* Microsoft Edge TTS
* Sentence-aware synthesis
* Audio pre-buffering
* Overlapped TTS generation
* Reduced playback latency

### Voice Interaction

* Browser-side Voice Activity Detection
* Automatic silence detection
* Hands-free conversation flow
* Interrupt support while assistant is speaking
* Real-time microphone volume visualization

### Frontend

* Modern futuristic UI
* Animated voice orb
* Live transcript display
* Conversation history
* Language indicator
* Responsive design

---

## 🏗️ Architecture

```text
Browser Microphone
        │
        ▼
Client-side VAD
        │
        ▼
WebSocket
        │
        ▼
FastAPI Backend
        │
        ├── Groq Whisper Large-v3
        │
        ├── Groq Llama 3.3 70B
        │
        └── Edge-TTS
        │
        ▼
Audio Response
        │
        ▼
Browser Playback
```

---

## 🛠️ Tech Stack

### Backend

* FastAPI
* WebSockets
* Uvicorn
* Python 3.10+

### AI Models

* Groq Whisper Large-v3
* Groq Llama 3.3 70B Versatile

### Speech

* Edge-TTS

### Frontend

* HTML
* CSS
* JavaScript

### Environment Management

* python-dotenv

---

## 📂 Project Structure

```text
.
├── app.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## 🚀 Installation

### 1. Clone Repository

```bash
git clone https://github.com/Kuldeep-amreliya/AI-voice-tutor.git
cd AI-voice-tutor
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
```

Windows

```bash
.venv\Scripts\activate
```

Linux / Mac

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create .env File

```env
GROQ_API_KEY=YOUR_API_KEY_HERE

GROQ_STT_MODEL=whisper-large-v3
GROQ_LLM_MODEL=llama-3.3-70b-versatile

PORT=8001

LLM_TEMPERATURE=0.6
LLM_MAX_TOKENS=512

SILENCE_MS=2000
SILENCE_THRESH=0.015
MIN_SPEECH_MS=1200
MIN_AUDIO_BYTES_KB=65

TTS_PREBUFFER_SENTENCES=2
MIN_CHUNK_WORDS=6
```

### 5. Run Application

```bash
python app.py
```

Open:

```text
http://localhost:8001
```

---

## 🔑 Environment Variables

| Variable                | Description                           |
| ----------------------- | ------------------------------------- |
| GROQ_API_KEY            | Groq API Key                          |
| GROQ_STT_MODEL          | Whisper model                         |
| GROQ_LLM_MODEL          | LLM model                             |
| PORT                    | Server port                           |
| LLM_TEMPERATURE         | Model temperature                     |
| LLM_MAX_TOKENS          | Maximum response tokens               |
| SILENCE_MS              | Silence duration before sending audio |
| SILENCE_THRESH          | VAD threshold                         |
| MIN_SPEECH_MS           | Minimum speech duration               |
| MIN_AUDIO_BYTES_KB      | Minimum audio size                    |
| TTS_PREBUFFER_SENTENCES | Number of buffered TTS sentences      |
| MIN_CHUNK_WORDS         | Minimum words per TTS chunk           |

---

## 🎯 Supported Languages

| Language | Voice                |
| -------- | -------------------- |
| English  | en-US-AndrewNeural   |
| Hindi    | hi-IN-MadhurNeural   |
| Gujarati | gu-IN-NiranjanNeural |

The first detected language is locked for the entire conversation session.

---

## ⚡ Optimizations Implemented

* Environment-variable based secret management
* Dedicated Whisper thread pool
* Hallucination filtering
* Sentence-aware TTS chunking
* Language locking
* Audio pre-buffering
* Overlapped TTS synthesis
* Interrupt handling
* Browser-side VAD
* Conversation memory management
* Temporary file cleanup
* Markdown sanitization for speech output

---

## 📸 Demo

Add screenshots or GIFs here.

```text
screenshots/
├── home.png
├── listening.png
├── speaking.png
└── conversation.png
```

---

## 🔒 Security

* No hardcoded API keys
* Environment-based configuration
* `.env` excluded via `.gitignore`
* Secret-safe GitHub workflow

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

Kuldeep Amareliya

GitHub:
https://github.com/Kuldeep-amreliya

LinkedIn:
https://www.linkedin.com/in/k-amreliyautm_source=share_via&utm_content=profile&utm_medium=member_android
