"""
VerifiNews - AI-Powered News Authenticity Analyzer
Main Flask application entry point.
"""

import os
import re
import json
import base64
import pickle
import logging
from flask import Flask, render_template, request, jsonify, Response, send_from_directory
from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq
from newsapi import NewsApiClient

# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

MODEL_PATH = os.path.join(BASE_DIR, "model", "news_classifier.sav")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_KEY_FALLBACK = os.environ.get("GEMINI_API_KEY_FALLBACK", "")
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")
NEWS_API_KEY_INDIA = os.environ.get("NEWS_API_KEY_INDIA", "")
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_API_KEY_FALLBACK = os.environ.get("GROQ_API_KEY_FALLBACK", "")

# Build list of Gemini API keys for fallback
GEMINI_API_KEYS = [k for k in [GEMINI_API_KEY, GEMINI_API_KEY_FALLBACK] if k]

# ---------------------------------------------------------------------------
# Language mappings: display_name -> newsapi_lang_code
# ---------------------------------------------------------------------------
LANGUAGE_MAP = {
    "en": ("en-IN", "en"),
    "hi": ("hi-IN", "en"),
    "te": ("te-IN", "en"),
    "ta": ("ta-IN", "en"),
    "kn": ("kn-IN", "en"),
    "ml": ("ml-IN", "en"),
    "bn": ("bn-IN", "en"),
    "mr": ("mr-IN", "en"),
    "gu": ("gu-IN", "en"),
    "pa": ("pa-IN", "en"),
    "ur": ("ur-IN", "en"),
    "or": ("od-IN", "en"),
    "as": ("as-IN", "en"),
    "ne": ("ne-IN", "en"),
    "sa": ("sa-IN", "en"),
    "kok": ("kok-IN", "en"),
    "mai": ("mai-IN", "en"),
    "doi": ("doi-IN", "en"),
    "sd": ("sd-IN", "en"),
    "ks": ("ks-IN", "en"),
    "mni": ("mni-IN", "en"),
    "sat": ("sat-IN", "en"),
    "brx": ("brx-IN", "en"),
    "ar": ("en-IN", "ar"),
    "fr": ("en-IN", "fr"),
    "de": ("en-IN", "de"),
    "es": ("en-IN", "es"),
    "pt": ("en-IN", "pt"),
    "ru": ("en-IN", "ru"),
    "zh": ("en-IN", "zh"),
}

# ---------------------------------------------------------------------------
# Image OCR is handled via Groq Vision (no Gemini Vision)
# ---------------------------------------------------------------------------

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(24).hex())
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB max upload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load trained model (sklearn Pipeline: TfidfVectorizer -> LogisticRegression)
# ---------------------------------------------------------------------------

try:
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    logger.info("Model loaded successfully from %s", MODEL_PATH)
except FileNotFoundError:
    logger.error("Model file not found at %s", MODEL_PATH)
    model = None
except Exception as exc:
    logger.error("Failed to load model: %s", exc)
    model = None

# ---------------------------------------------------------------------------
# Gemini AI Verification
# ---------------------------------------------------------------------------

# Build Gemini clients for each available API key (for graceful fallback)
gemini_clients = []
for _gk in GEMINI_API_KEYS:
    try:
        gemini_clients.append(genai.Client(
            api_key=_gk,
            http_options={"timeout": 60_000},  # 60 s hard timeout
        ))
    except Exception as _exc:
        logger.warning("Failed to create Gemini client: %s", _exc)

if gemini_clients:
    gemini_client = gemini_clients[0]  # primary client
    logger.info("Gemini AI configured successfully (%d API key(s))", len(gemini_clients))
else:
    gemini_client = None
    logger.warning("No Gemini API keys set; AI verification disabled")

# ---------------------------------------------------------------------------
# NewsAPI Client
# ---------------------------------------------------------------------------

if NEWS_API_KEY:
    newsapi_client = NewsApiClient(api_key=NEWS_API_KEY)
    logger.info("NewsAPI configured successfully")
else:
    newsapi_client = None
    logger.warning("NEWS_API_KEY not set; NewsAPI verification disabled")

if NEWS_API_KEY_INDIA:
    newsapi_client_india = NewsApiClient(api_key=NEWS_API_KEY_INDIA)
    logger.info("NewsAPI (India) configured successfully")
else:
    newsapi_client_india = None

# ---------------------------------------------------------------------------
# Groq Client (Vision OCR)
# ---------------------------------------------------------------------------

GROQ_API_KEYS = [k for k in [GROQ_API_KEY, GROQ_API_KEY_FALLBACK] if k]

groq_clients = []
for _gk in GROQ_API_KEYS:
    try:
        groq_clients.append(Groq(api_key=_gk))
    except Exception as _exc:
        logger.warning("Failed to create Groq client: %s", _exc)

if groq_clients:
    groq_client = groq_clients[0]
    logger.info("Groq Vision OCR configured (%d API key(s))", len(groq_clients))
else:
    groq_client = None
    logger.warning("GROQ_API_KEY not set; Vision OCR disabled")

# Gemini model — always use gemini-2.5-flash
GEMINI_MODEL = "gemini-2.5-flash"


WORLD_CONTEXT_2025_2026 = """
VERIFIED WORLD EVENTS (2025-2026) — Use these as GROUND TRUTH for fact-checking:

=== GLOBAL POLITICS ===
- USA: Donald Trump returned to office Jan 20, 2025, second term. Over 225 executive orders in first year. Sweeping tariffs on China/Mexico. "One Big Beautiful Bill" triggered federal spending cuts.
- Vatican: Pope Francis passed away April 2025. Succeeded May 2025 by Pope Leo XIV (Cardinal Robert Prevost) — first US-born Pope.
- Venezuela: US launched military operation Jan 2026 to remove Nicolás Maduro. Massive US military buildup off Venezuelan coast as of March 2026.

=== RUSSIA-UKRAINE WAR ===
- Russia controls ~20% of Ukrainian territory (~45,800 sq miles) as of March 2026.
- Feb 2026: Russia's smallest monthly gain since 2024 (~49 sq miles) — grinding stalemate.
- Trump placed himself at center of peace negotiations; no formal ceasefire achieved.

=== IRAN-US WAR (Operation Epic Fury) ===
- Feb 28, 2026: US and Israel launched over 900 strikes in first 12 hours.
- Ayatollah Ali Khamenei killed in opening strikes along with dozens of top officials.
- Iran retaliated with hundreds of ballistic missiles and thousands of drones — hit US bases in Qatar (Al-Udeid), Bahrain, UAE.
- March 2, 2026: Iran declared Strait of Hormuz closed. Over 130 ships locked in Persian Gulf.
- Over 1,300 killed in first week. Oil prices surging. Maersk/Hapag-Lloyd suspended transit.
- Indian sailors killed in drone attacks on tankers. ~1 crore Indians at risk in Gulf.
- As of March 8, 2026: US claims 90% of Iran's missile capability degraded. Trump says "no deal except unconditional surrender."

=== ISRAEL-PALESTINE & MIDDLE EAST ===
- Gaza high-intensity phase (2023-2025) wound down; Strip remains humanitarian disaster.
- "Board of Peace" and "National Transitional Committee" established early 2026 for reconstruction.
- US and Israel engaged in active operations against Iran and Houthis.

=== CIVIL WARS ===
- Sudan: Civil war intensified in Kordofan region (March 2026). Drone strikes on hospitals.
- Myanmar: Military junta controls only ~21% of territory; rebel forces hold 42%. Magnitude 7.7 earthquake March 2025.

=== CHINA-TAIWAN ===
- China using drone signal spoofing (false aircraft signals) over South China Sea.
- Trump admin delayed major weapons sale to Taiwan (Feb 2026), pending Xi-Trump Summit late March 2026.

=== AI & TECHNOLOGY ===
- 2025 was "Year of the AI Agent" — focus shifted from chatbots to Agentic AI.
- Major model releases: GPT-5 (late 2025), Gemini 3.1 (early 2026), Llama 4 family (April 2025).
- Token costs dropped 280-fold; focus shifted from training to efficient deployment.
- Bitcoin ATH $126,080 (Oct 2025), corrected to ~$80k-$90k by early 2026.

=== SCIENCE & HEALTH ===
- 2025 Breakthrough Prize: David Liu for revolutionary gene-editing platforms.
- FDA approved Suzetrigine (Journavax) early 2025 — first non-addictive opioid-free pain reliever in decades.
- Tandem perovskite-silicon solar cells hit 34% efficiency record in 2025.

=== SPORTS ===
- India women won 2025 ICC Women's ODI World Cup in Navi Mumbai.
- Virat Kohli and Rohit Sharma retired from Test cricket late 2025.
- FIFA 2026 World Cup (USA/Mexico/Canada) — expanded 48-team format.
- ICC Men's T20 World Cup 2026 co-hosted by India and Sri Lanka (Feb 7 – March 8, 2026). India defeated England in semifinal at Wankhede.
- Footballer Diogo Jota passed away in 2025.
- Charlie Kirk assassinated September 2025.

=== INDIA ===
- New Income Tax Act 2025 replaces 60-year-old 1961 Act; effective April 1, 2026. Taxpayers up to ₹12.75 lakh exempted.
- India GDP growth projected 6.6%-6.9% for 2026. Fastest-growing major economy.
- Landmark trade deal with US (Feb 2026) reducing tariffs from 25% to 18%.
- IndiaAI Mission, India Semiconductor Mission 2.0 launched.
- AI Impact Expo 2026 in New Delhi (Feb 2026) — 300+ AI startups.
- Navi Mumbai International Airport (NMIA) operational late 2025.
- Mumbai-Ahmedabad Bullet Train: major undersea tunnel sections completed early 2026.
- Mumbai Metro Line 3 (Aqua Line) fully operational 2025.
- Four Labour Codes implemented Nov 2025 (consolidating 29 laws).
- Waqf Act renamed to UMEED Act 1995 (late 2025).
- Gaganyaan mission (crewed low Earth orbit) is India's current human spaceflight focus — manned Moon mission aspirations target ~2040.

=== TELANGANA ===
- ₹3.05 lakh crore 2025-26 budget. Six Guarantees (₹56,000 crore): Mahalakshmi Scheme, Gruha Jyothi, Rythu Bharosa.
- CM Revanth Reddy: Trillion-dollar economy goal by 2033.
- Future City (30,000 acres) at Mucherla — India's first net-zero smart city.
- Musi Riverfront Rejuvenation project (55km).
- Hyderabad Metro Phase 2: 76.4 km expansion.
- Regional Ring Road (RRR): 340 km project.
- Shiv Pratap Shukla appointed new Governor (March 7, 2026).
- K. Kavitha announced new regional political party (March 6, 2026).
- 130 CPI(Maoist) cadres surrendered before CM Revanth Reddy (March 7, 2026).
- E-scooters for female college students announced March 8, 2026.
- Goal to remove all 2,800 diesel RTC buses from Hyderabad by Dec 2026, replace with EVs.
"""


# Google Search grounding tool for real-time web search
_google_search_tool = types.Tool(google_search=types.GoogleSearch())
_grounded_config = types.GenerateContentConfig(tools=[_google_search_tool])


def _call_gemini(contents, use_grounding=False):
    """Call Gemini 2.5 Flash, cycling through all API keys on failure.
    If use_grounding=True, enables Google Search grounding for real-time web results.
    Falls back to non-grounding call if grounding fails."""
    last_error = None
    for client in gemini_clients:
        try:
            kwargs = dict(model=GEMINI_MODEL, contents=contents)
            if use_grounding:
                kwargs["config"] = _grounded_config
            response = client.models.generate_content(**kwargs)
            return response
        except Exception as exc:
            last_error = exc
            logger.warning("Gemini %s failed (key ending ...%s): %s",
                           GEMINI_MODEL, str(getattr(client, '_api_key', ''))[-4:], exc)
            continue
    # If grounding calls all failed, retry WITHOUT grounding as fallback
    if use_grounding and last_error:
        logger.info("Retrying Gemini WITHOUT grounding as fallback...")
        for client in gemini_clients:
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL, contents=contents)
                return response
            except Exception as exc:
                last_error = exc
                continue
    if last_error:
        logger.error("All Gemini API keys exhausted. Last error: %s", last_error)
    return None


def gemini_verify(text):
    """Use Gemini AI with Google Search grounding to verify a news claim."""
    if not gemini_clients:
        return None

    prompt = (
        "You are a professional fact-checker and predictive analyst. "
        "The current date is March 8, 2026. "
        "You have access to the following VERIFIED information about major events in 2025-2026. "
        "Use this as ground truth when evaluating claims:\n\n"
        f"{WORLD_CONTEXT_2025_2026}\n\n"
        "INSTRUCTIONS:\n"
        "You MUST use Google Search to look up the latest real-time information about this claim. "
        "Cross-reference search results AND the verified events above to determine truth. "
        "Analyze the following news statement and determine whether it is TRUE or FALSE. "
        "You MUST pick one — either TRUE or FALSE. "
        "Do NOT say UNVERIFIABLE, UNCERTAIN, or anything else. You must commit to TRUE or FALSE.\n\n"
        "Respond ONLY with valid JSON (no markdown, no code fences) in this exact format:\n"
        '{"verdict": "TRUE" or "FALSE", '
        '"confidence": 0-100, '
        '"reason": "brief 1-2 sentence explanation"}\n\n'
        f'Statement: "{text}"'
    )

    try:
        # Use grounding=True so Gemini can search the web in real time
        response = _call_gemini(prompt, use_grounding=True)
        if response is None:
            logger.warning("Gemini returned None — all API calls failed")
            return None

        # Safely extract text from response
        try:
            raw = response.text.strip()
        except Exception as tex:
            logger.warning("Gemini response has no text: %s", tex)
            return None

        logger.info("Gemini raw response (first 300 chars): %s", raw[:300])

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        # Try direct JSON parse first
        result = None
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: extract JSON object with regex
            m = re.search(r'\{[^{}]*"verdict"[^{}]*\}', raw)
            if m:
                try:
                    result = json.loads(m.group())
                except json.JSONDecodeError:
                    pass

        if result is None:
            logger.warning("Could not parse JSON from Gemini response: %s", raw[:200])
            return None

        # Extract grounding sources (deduplicated, max 5)
        grounding_sources = []
        try:
            candidate = response.candidates[0]
            if candidate.grounding_metadata and candidate.grounding_metadata.grounding_chunks:
                seen_urls = set()
                for chunk in candidate.grounding_metadata.grounding_chunks:
                    if chunk.web and chunk.web.uri and chunk.web.uri not in seen_urls:
                        seen_urls.add(chunk.web.uri)
                        grounding_sources.append({
                            "title": chunk.web.title or "",
                            "url": chunk.web.uri,
                        })
                        if len(grounding_sources) >= 5:
                            break
        except Exception:
            pass

        if "verdict" in result and "reason" in result:
            verdict = str(result["verdict"]).upper()
            if verdict not in ("TRUE", "FALSE"):
                verdict = "FALSE"
            return {
                "verdict": verdict,
                "confidence": int(result.get("confidence", 50)),
                "reason": str(result["reason"]),
                "grounding_sources": grounding_sources,
            }
        logger.warning("Gemini JSON missing verdict/reason keys: %s", result)
        return None
    except Exception as exc:
        logger.warning("Gemini verify error: %s (type: %s)", exc, type(exc).__name__)
        return None


def newsapi_verify(text, language="en"):
    """
    Use NewsAPI to cross-reference the claim against real news articles.
    Combines results from the primary key and the India-specific key.
    Uses OR-based keyword queries and multiple strategies for better recall.
    Returns a dict with match_score (0-100), num_matches, and matched articles.
    """
    if newsapi_client is None and newsapi_client_india is None:
        return None

    # Resolve NewsAPI language code
    _, newsapi_lang = LANGUAGE_MAP.get(language, ("en-IN", "en"))

    try:
        # Extract keywords: remove common stop words and short words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "shall", "can", "to", "of", "in", "for",
            "on", "with", "at", "by", "from", "as", "into", "through", "during",
            "before", "after", "above", "below", "between", "out", "off", "over",
            "under", "again", "further", "then", "once", "that", "this", "these",
            "those", "it", "its", "and", "but", "or", "nor", "not", "so", "very",
            "just", "about", "up", "down", "here", "there", "when", "where", "how",
            "all", "each", "every", "both", "few", "more", "most", "other", "some",
            "such", "no", "only", "own", "same", "than", "too", "also", "says",
            "said", "according", "new", "now", "year", "years",
        }
        words = re.findall(r'[a-zA-Z]+', text.lower())
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]

        if not keywords:
            return None

        # Strategy: Use OR logic with top keywords for broader matching
        # Pick top 5 most significant keywords (longer words first as proxy for importance)
        ranked_kw = sorted(keywords, key=lambda w: len(w), reverse=True)
        top_kw = list(dict.fromkeys(ranked_kw))[:6]  # deduplicate, keep order
        or_query = " OR ".join(top_kw)

        # Also build a short phrase query from original word order for precision
        phrase_kw = list(dict.fromkeys(keywords))[:4]
        phrase_query = " ".join(phrase_kw)

        articles = []
        total_results = 0

        def _fetch_everything(client, query, lang):
            """Fetch articles using get_everything endpoint."""
            try:
                resp = client.get_everything(
                    q=query, language=lang, sort_by="relevancy", page_size=10,
                )
                return resp.get("articles", []), resp.get("totalResults", 0)
            except Exception as exc:
                logger.warning("NewsAPI get_everything error (q=%s): %s", query[:50], exc)
                return [], 0

        def _fetch_headlines(client, query):
            """Fetch articles using get_top_headlines endpoint (no language filter)."""
            try:
                resp = client.get_top_headlines(
                    q=query, page_size=10,
                )
                return resp.get("articles", []), resp.get("totalResults", 0)
            except Exception as exc:
                logger.warning("NewsAPI get_top_headlines error (q=%s): %s", query[:50], exc)
                return [], 0

        # --- Primary API key: OR query + phrase query + top headlines ---
        if newsapi_client is not None:
            a1, t1 = _fetch_everything(newsapi_client, or_query, newsapi_lang)
            articles.extend(a1)
            total_results += t1
            # If OR query returned few results, also try phrase query
            if t1 < 5:
                a2, t2 = _fetch_everything(newsapi_client, phrase_query, newsapi_lang)
                articles.extend(a2)
                total_results += t2
            # Also search top headlines with shortest meaningful query
            a3, t3 = _fetch_headlines(newsapi_client, " ".join(top_kw[:3]))
            articles.extend(a3)
            total_results += t3

        # --- India API key: same multi-strategy approach ---
        if newsapi_client_india is not None:
            a4, t4 = _fetch_everything(newsapi_client_india, or_query, newsapi_lang)
            articles.extend(a4)
            total_results += t4
            if t4 < 5:
                a5, t5 = _fetch_everything(newsapi_client_india, phrase_query, newsapi_lang)
                articles.extend(a5)
                total_results += t5
            a6, t6 = _fetch_headlines(newsapi_client_india, " ".join(top_kw[:3]))
            articles.extend(a6)
            total_results += t6

        # Deduplicate by URL
        seen_urls = set()
        unique_articles = []
        for a in articles:
            url = a.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(a)
        articles = unique_articles

        if not articles:
            return {
                "match_score": 0,
                "num_matches": 0,
                "total_results": 0,
                "articles": [],
                "verdict": "FALSE",
            }

        # Score each article for relevance — STRICT filtering
        # An article must share a meaningful portion of the claim's key terms
        # to be considered "related". This prevents random news from appearing.
        MIN_RELEVANCE = 50  # minimum % keyword overlap to count as related

        text_words = set(keywords)
        scored_articles = []

        for article in articles[:15]:
            title = (article.get("title") or "").lower()
            description = (article.get("description") or "").lower()
            content = (article.get("content") or "").lower()
            combined_text = f"{title} {description} {content}"

            # Calculate word overlap
            article_words = set(re.findall(r'[a-zA-Z]+', combined_text))
            article_words = {w for w in article_words if len(w) > 2 and w not in stop_words}

            if text_words:
                overlap = len(text_words & article_words) / len(text_words)
            else:
                overlap = 0

            relevance_pct = round(overlap * 100, 1)

            # Only keep articles that meet the minimum relevance threshold
            if relevance_pct >= MIN_RELEVANCE:
                scored_articles.append({
                    "title": article.get("title", ""),
                    "source": (article.get("source") or {}).get("name", "Unknown"),
                    "url": article.get("url", ""),
                    "relevance": relevance_pct,
                })

        # Sort by relevance descending
        scored_articles.sort(key=lambda a: a["relevance"], reverse=True)
        matched_articles = scored_articles[:5]

        if not matched_articles:
            return {
                "match_score": 0,
                "num_matches": 0,
                "total_results": 0,
                "articles": [],
                "verdict": "FALSE",
            }

        # Calculate overall match score from the related articles only
        relevance_scores = [a["relevance"] / 100.0 for a in matched_articles]
        avg_relevance = sum(relevance_scores) / len(relevance_scores)
        top_relevance = max(relevance_scores)
        raw_score = 0.6 * top_relevance + 0.4 * avg_relevance
        match_score = min(raw_score * 100, 100)

        verdict = "TRUE" if match_score >= 35 else "FALSE"

        return {
            "match_score": round(match_score, 1),
            "num_matches": len(matched_articles),
            "total_results": total_results,
            "articles": matched_articles,
            "verdict": verdict,
        }
    except Exception as exc:
        logger.warning("NewsAPI verification error: %s", exc)
        return None


def extract_text_from_image(image_file):
    """Extract text from an uploaded image using Groq Vision.
    Images are NEVER sent to Gemini — only the extracted text is."""
    image_bytes = image_file.read()
    if not image_bytes:
        logger.warning("Empty image file received")
        return None

    if not groq_clients:
        logger.error("Groq API key not configured — cannot perform OCR")
        return None

    b64 = base64.b64encode(image_bytes).decode("utf-8")

    # Detect MIME type from file extension
    ext = os.path.splitext(image_file.filename or "image.png")[1].lower()
    mime_map = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".bmp": "image/bmp", ".gif": "image/gif", ".webp": "image/webp",
        ".tiff": "image/tiff",
    }
    mime = mime_map.get(ext, "image/png")

    last_error = None
    for client in groq_clients:
        try:
            completion = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract all text from this image. Return only the raw text, nothing else."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"}
                        }
                    ]
                }],
                max_completion_tokens=1024,
            )

            extracted = completion.choices[0].message.content.strip()
            if extracted:
                logger.info("Groq Vision OCR extracted %d chars", len(extracted))
                return extracted

            logger.info("Groq Vision returned empty text")
            return None
        except Exception as exc:
            last_error = exc
            logger.warning("Groq Vision OCR failed (cycling to next key): %s", exc)
            continue

    logger.warning("All Groq API keys exhausted. Last error: %s", last_error)
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.route("/")
def home():
    """Render the main analysis page."""
    return render_template("index.html")


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    """Serve files from the assets folder."""
    return send_from_directory(os.path.join(BASE_DIR, "assets"), filename)


@app.route("/ocr", methods=["POST"])
def ocr_extract():
    """Extract text from an uploaded image using Groq Vision."""
    if "image" not in request.files:
        return jsonify({"error": "No image file provided."}), 400

    image_file = request.files["image"]
    if image_file.filename == "":
        return jsonify({"error": "No image selected."}), 400

    # Validate file type
    allowed_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".gif", ".webp"}
    ext = os.path.splitext(image_file.filename)[1].lower()
    if ext not in allowed_extensions:
        return jsonify({"error": f"Unsupported file type: {ext}. Use PNG, JPG, BMP, or TIFF."}), 400

    extracted_text = extract_text_from_image(image_file)

    if not extracted_text:
        return jsonify({"error": "Could not extract text from the image. Please try a clearer image."}), 422

    return jsonify({"text": extracted_text})


@app.route("/analyze", methods=["POST"])
def analyze():
    """Analyze a news statement and return prediction results as JSON."""
    if model is None:
        return jsonify({"error": "Model is not available. Please check server logs."}), 503

    data = request.get_json(silent=True)
    if not data or not data.get("text", "").strip():
        return jsonify({"error": "Please provide a news statement to analyze."}), 400

    news_text = data["text"].strip()
    language = data.get("language", "en")

    try:
        # --- Step 1: ML Model Analysis ---
        probabilities = model.predict_proba([news_text])[0]

        label_map = {label: prob for label, prob in zip(model.classes_, probabilities)}
        truth_score = float(label_map.get(True, label_map.get("TRUE", 0)))
        fake_score = float(label_map.get(False, label_map.get("FALSE", 0)))

        ml_truth = round(truth_score * 100, 1)
        ml_fake = round(fake_score * 100, 1)
        ml_confidence = round(max(truth_score, fake_score) * 100, 1)
        ml_verdict = "Real" if truth_score > fake_score else "Fake"

        analysis_steps = []
        analysis_steps.append({
            "step": "Text Preprocessing",
            "detail": f"Input text ({len(news_text)} chars) processed through TF-IDF vectorizer with n-gram features",
            "status": "complete",
        })
        analysis_steps.append({
            "step": "ML Classification",
            "detail": f"Logistic Regression model classified this statement as {ml_verdict}",
            "status": "complete",
        })

        # --- Step 2: NewsAPI Cross-Reference (70% weight) ---
        newsapi_result = newsapi_verify(news_text, language=language)
        newsapi_step = {
            "step": "News Source Cross-Reference",
            "detail": "",
            "status": "complete",
        }

        # --- Step 3: Gemini AI Verification ---
        ai_result = gemini_verify(news_text)
        ai_step = {
            "step": "Deep Semantic Analysis",
            "detail": "",
            "status": "complete",
        }

        # --- Step 4: Compute Final Combined Score ---
        # Start with ML model score as base
        final_truth = truth_score
        final_fake = fake_score
        components_used = ["ML Model"]

        # NewsAPI: only factor in when articles were actually found with
        # meaningful relevance – this way 0-result queries never drag the
        # score negatively; NewsAPI can only *boost* confidence.
        has_news_sources = (newsapi_result is not None
                           and newsapi_result.get("num_matches", 0) > 0
                           and newsapi_result.get("match_score", 0) > 10)

        if has_news_sources:
            news_score = newsapi_result["match_score"] / 100.0
            if newsapi_result["verdict"] == "TRUE":
                news_truth = news_score
                news_fake = 1.0 - news_score
            else:
                news_truth = 1.0 - news_score
                news_fake = news_score

            newsapi_step["detail"] = (
                f"Found {newsapi_result['total_results']} related articles across "
                f"{newsapi_result['num_matches']} sources. "
                f"Relevance match: {newsapi_result['match_score']}%"
            )
            components_used.append("News Sources")
        else:
            news_truth = 0.5
            news_fake = 0.5
            if newsapi_result is not None and newsapi_result.get("total_results", 0) == 0:
                newsapi_step["detail"] = "No related news articles found — score unaffected"
            elif newsapi_result is not None:
                newsapi_step["detail"] = (
                    f"Found {newsapi_result.get('total_results', 0)} articles but relevance too low to affect score"
                )
            else:
                newsapi_step["detail"] = "News source cross-referencing unavailable"
            newsapi_step["status"] = "skipped"

        # Gemini AI contribution
        if ai_result is not None:
            gemini_conf = ai_result["confidence"] / 100.0
            if ai_result["verdict"] == "TRUE":
                ai_truth = gemini_conf
                ai_fake = 1.0 - gemini_conf
            else:
                ai_truth = 1.0 - gemini_conf
                ai_fake = gemini_conf

            ai_step["detail"] = (
                f"Semantic analysis verdict: {ai_result['verdict']} "
                f"({ai_result['confidence']}% confidence). "
                f"{ai_result['reason']}"
            )
            components_used.append("Semantic Analysis")
        else:
            ai_truth = 0.5
            ai_fake = 0.5
            ai_step["detail"] = "Semantic analysis unavailable"
            ai_step["status"] = "skipped"

        analysis_steps.append(newsapi_step)
        analysis_steps.append(ai_step)

        if ai_result is not None and has_news_sources:
            ml_weight, ai_weight, news_weight = 0.25, 0.50, 0.25
        elif ai_result is not None:
            ml_weight, ai_weight, news_weight = 0.25, 0.75, 0.0
        elif has_news_sources:
            ml_weight, ai_weight, news_weight = 0.75, 0.0, 0.25
        else:
            ml_weight, ai_weight, news_weight = 1.0, 0.0, 0.0

        blended_truth = ml_weight * truth_score
        blended_fake = ml_weight * fake_score
        if ai_result is not None:
            blended_truth += ai_weight * ai_truth
            blended_fake += ai_weight * ai_fake
        if has_news_sources:
            blended_truth += news_weight * news_truth
            blended_fake += news_weight * news_fake

        # Normalize to 100%
        total = blended_truth + blended_fake
        if total > 0:
            final_truth_pct = round((blended_truth / total) * 100, 1)
            final_fake_pct = round((blended_fake / total) * 100, 1)
        else:
            final_truth_pct = ml_truth
            final_fake_pct = ml_fake

        is_real = final_truth_pct > final_fake_pct
        final_confidence = round(max(final_truth_pct, final_fake_pct), 1)

        analysis_steps.append({
            "step": "Final Verdict Computation",
            "detail": (
                f"Aggregated {len(components_used)} verification sources: "
                f"{', '.join(components_used)}. "
                f"Final score: {final_confidence}% confidence"
            ),
            "status": "complete",
        })

        # Build news articles for display (if any)
        news_articles = []
        if newsapi_result and newsapi_result.get("articles"):
            news_articles = newsapi_result["articles"]

        return jsonify({
            "prediction": "Real" if is_real else "Fake",
            "is_real": is_real,
            "confidence": final_confidence,
            "truth_probability": final_truth_pct,
            "fake_probability": final_fake_pct,
            "analysis_steps": analysis_steps,
            "news_articles": news_articles,
            "gemini_reason": ai_result["reason"] if ai_result else None,
            "grounding_sources": ai_result.get("grounding_sources", []) if ai_result else [],
        })
    except Exception as exc:
        logger.exception("Prediction failed")
        return jsonify({"error": f"Analysis failed: {str(exc)}"}), 500


@app.route("/health")
def health():
    """Health-check endpoint."""
    return jsonify({
        "status": "healthy" if model is not None else "degraded",
        "model_loaded": model is not None,
        "newsapi_available": newsapi_client is not None or newsapi_client_india is not None,
        "gemini_available": gemini_client is not None,
    })


@app.route("/tts", methods=["POST"])
def tts():
    """Convert text to speech using Deepgram API and return audio."""
    if not DEEPGRAM_API_KEY:
        return jsonify({"error": "TTS not configured"}), 503

    data = request.get_json(silent=True)
    if not data or not data.get("text", "").strip():
        return jsonify({"error": "No text provided"}), 400

    text = data["text"].strip()[:2000]  # Limit to 2000 chars

    try:
        import requests as req
        resp = req.post(
            "https://api.deepgram.com/v1/speak?model=aura-2-thalia-en",
            headers={
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"text": text},
            timeout=30,
        )
        if resp.status_code != 200:
            logger.warning("Deepgram TTS error: %s %s", resp.status_code, resp.text[:200])
            return jsonify({"error": "TTS generation failed"}), 502

        return Response(resp.content, mimetype="audio/mpeg")
    except Exception as exc:
        logger.warning("TTS error: %s", exc)
        return jsonify({"error": "TTS generation failed"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
