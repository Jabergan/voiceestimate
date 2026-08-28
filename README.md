# VoiceEstimate

> Voice to professional estimate in seconds. Built for contractors in the field.

**Hackyard 2026** — Built live August 28–30, 2026.

---

## The Problem

Contractors lose jobs because estimates take too long. A framer finishes a walkthrough, drives home, opens Excel, and spends an hour typing. By then the homeowner already called someone else.

## The Solution

Open the app. Hit record. Describe the job out loud — materials, labor, square footage. Done. A professional PDF estimate is generated in seconds, ready to email before you leave the driveway.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python / Flask |
| Speech-to-Text | faster-whisper (Whisper small, GPU) |
| AI Parse | Qwen3 8B via Ollama (local, zero cost) |
| PDF Generation | ReportLab |
| History | SQLite |
| Email | Gmail SMTP |

## Features

- 🎙 **Voice input** — record your job description on any device
- ⚡ **Instant parse** — Qwen3 extracts line items, quantities, units, and prices
- 📄 **PDF generation** — professional contractor estimate, download instantly
- 📧 **Email to customer** — send the PDF before leaving the job site
- 📋 **Estimate history** — every estimate saved, retrievable anytime
- 💰 **Customizable rates** — set your own labor rates per trade

## Setup

### Requirements

- Python 3.10+
- CUDA-capable GPU (recommended) or CPU
- [Ollama](https://ollama.ai) running locally with `qwen3:8b` pulled
- ffmpeg installed

### Install

```bash
git clone https://github.com/Jabergan/voiceestimate.git
cd voiceestimate
pip install -r requirements.txt
ollama pull qwen3:8b
```

### Configure

```bash
cp .env.example .env
# Edit .env and add your Gmail app password
```

### Run

```bash
bash start.sh
# App runs on http://localhost:5055
```

## Usage

1. Open the app in your browser
2. Enter contractor name, customer name, and job address
3. Hit the microphone button and describe the job
4. Hit **Parse Line Items**
5. Review and adjust if needed
6. Hit **Download PDF** or **Email to Customer**

## Why Local AI?

No API costs. No latency. No data leaving the job site. Qwen3 8B runs entirely on local hardware — a $400 GPU handles it in under 3 seconds.

---

*Built by Jamie Bergan — Minot, ND*
