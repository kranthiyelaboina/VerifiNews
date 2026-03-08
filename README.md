<div align="center">

# 🛡️ VerifiNews — AI-Powered News Authenticity Analyzer

**Multi-source verification pipeline combining ML, AI semantic analysis, and real-time news cross-referencing to detect misinformation.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-2.3+-000000?style=for-the-badge&logo=flask)
![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Usage](#-usage)
- [API Keys](#-api-keys)
- [API Reference](#-api-reference)
- [Dataset](#-dataset)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔍 Overview

**VerifiNews** is a web application that analyzes news statements through a multi-layered verification pipeline:

1. **ML Classification** — A trained Logistic Regression model with TF-IDF vectorization
2. **Gemini AI Analysis** — Deep semantic analysis using Google Gemini 2.5 Flash with real-time Google Search grounding
3. **NewsAPI Cross-Reference** — Cross-references claims against 150,000+ news sources

The system aggregates results from all verification sources to produce a final confidence-scored verdict.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| **Multi-Source Verification** | Combines ML, AI, and news cross-referencing for accurate results |
| **Google Search Grounding** | Real-time web search via Gemini to surface 5 verified source websites |
| **Image OCR** | Extract text from newspaper images using Groq Vision (Llama 4 Scout) |
| **30+ Languages** | Supports all major Indian and international languages |
| **Text-to-Speech** | Listen to analysis insights via Deepgram TTS |
| **Immersive UI** | Dark theme with video background, animated verification pipeline overlay |
| **Intro Video** | Cinematic intro animation on page load |
| **API Key Fallback** | Automatic failover for Gemini and Groq API keys |
| **REST API** | JSON-based endpoints for programmatic access |

---

## 🏗️ Architecture

```
User Input (Text / Image)
        │
        ├── Image? ──► Groq Vision OCR ──► Extracted Text
        │
        ▼
┌──────────────────────────────────────────────┐
│            Verification Pipeline             │
│                                              │
│  ┌─────────────┐  ┌──────────────────────┐   │
│  │  TF-IDF +   │  │  Gemini 2.5 Flash    │   │
│  │  Logistic   │  │  + Google Search     │   │
│  │  Regression │  │    Grounding         │   │
│  └──────┬──────┘  └──────────┬───────────┘   │
│         │                    │               │
│  ┌──────┴────────────────────┴───────────┐   │
│  │        NewsAPI Cross-Reference        │   │
│  │      (150,000+ news sources)          │   │
│  └──────────────────┬────────────────────┘   │
│                     │                        │
│         ┌───────────▼───────────┐            │
│         │  Aggregated Verdict   │            │
│         │  + Confidence Score   │            │
│         └───────────────────────┘            │
└──────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
VerifiNews/
├── app.py                    # Flask application & verification logic
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (API keys)
├── .gitignore                # Git ignore rules
├── README.md                 # This file
│
├── model/
│   └── news_classifier.sav   # Trained sklearn pipeline (TF-IDF + LR)
│
├── assets/
│   └── intro.mp4             # Intro video
│
├── data/
│   ├── train.csv             # Training dataset (10,240 samples)
│   ├── test.csv              # Test dataset (1,284 samples)
│   ├── valid.csv             # Validation dataset (1,267 samples)
│   └── liar_dataset/         # Original LIAR dataset (TSV)
│
├── templates/
│   └── index.html            # Main HTML template
│
└── static/
    ├── css/style.css         # Dark theme styles
    ├── js/main.js            # Frontend logic
    └── assets/               # Static media (background video etc.)
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**
- API keys for: Gemini AI, NewsAPI, Groq, Deepgram (see [API Keys](#-api-keys))

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/VerifiNews.git
   cd VerifiNews
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**

   Create a `.env` file in the project root:
   ```env
   GEMINI_API_KEY=your_gemini_api_key
   GEMINI_API_KEY_FALLBACK=your_fallback_gemini_key
   NEWS_API_KEY=your_newsapi_key
   NEWS_API_KEY_INDIA=your_newsapi_india_key
   DEEPGRAM_API_KEY=your_deepgram_key
   GROQ_API_KEY=your_groq_api_key
   GROQ_API_KEY_FALLBACK=your_fallback_groq_key
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

6. **Open in browser:**
   ```
   http://127.0.0.1:5000
   ```

---

## 💡 Usage

### Web Interface

1. Navigate to `http://127.0.0.1:5000`
2. Wait for the intro video to finish
3. Enter a news statement or upload a newspaper image
4. Click **"Analyze Statement"**
5. Watch the verification pipeline process in real-time
6. View the verdict, confidence score, analysis insight, news sources, and Google Search sources

### API Usage

```bash
curl -X POST http://127.0.0.1:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"text": "India successfully landed on the Moon in 2025", "language": "en"}'
```

---

## 🔑 API Keys

| Service | Purpose | Get Key |
|---------|---------|---------|
| **Gemini AI** | Semantic analysis + Google Search grounding | [Google AI Studio](https://aistudio.google.com/) |
| **NewsAPI** | News article cross-referencing | [newsapi.org](https://newsapi.org/) |
| **Groq** | Image OCR via Llama 4 Scout Vision | [console.groq.com](https://console.groq.com/) |
| **Deepgram** | Text-to-Speech for analysis insights | [deepgram.com](https://deepgram.com/) |

All services support fallback API keys for high availability.

---

## 📡 API Reference

### `POST /analyze`

Analyze a news statement.

**Request:**
```json
{
  "text": "Your news statement here",
  "language": "en"
}
```

**Response:**
```json
{
  "prediction": "Real",
  "is_real": true,
  "confidence": 85.2,
  "truth_probability": 85.2,
  "fake_probability": 14.8,
  "analysis_steps": [...],
  "gemini_reason": "Analysis explanation...",
  "news_articles": [...],
  "grounding_sources": [...]
}
```

### `POST /ocr`

Extract text from an uploaded image.

**Request:** `multipart/form-data` with `image` file field

**Response:**
```json
{ "text": "Extracted text from image" }
```

### `GET /health`

Health check endpoint.

### `POST /tts`

Convert text to speech (returns audio/mpeg).

---

## 📊 Dataset

Built on the **LIAR dataset** — a benchmark for fake news detection:

> Wang, W. Y. (2017). "Liar, Liar Pants on Fire": A New Benchmark Dataset for Fake News Detection. *ACL 2017.*

| Split | Samples |
|-------|:-------:|
| Training | 10,240 |
| Testing | 1,284 |
| Validation | 1,267 |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m 'Add new feature'`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## ⚠️ Disclaimer

This tool uses machine learning and multi-source verification for analysis and should be used as one of many methods to evaluate news credibility. Always cross-reference with trusted sources.

---

## 📄 License

MIT License — For educational and research purposes.

---

<div align="center">

**Built with ❤️ using Python, Flask, Gemini AI & scikit-learn**

</div>
