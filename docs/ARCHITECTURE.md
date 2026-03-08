# VerifiNews — Architecture Documentation

## System Overview

VerifiNews is built as a lightweight, single-service web application that combines a Python/Flask backend with a modern vanilla JavaScript frontend. The system loads a pre-trained scikit-learn pipeline at startup and uses it to classify news statements in real time.

---

## Component Diagram

```
┌─────────────────────────────────────────────────┐
│                    Browser                       │
│                                                  │
│  index.html + style.css + main.js               │
│  ┌────────────┐    AJAX (JSON)    ┌───────────┐ │
│  │  Textarea  │ ─────────────────►│  /analyze  ││
│  │  + UI      │ ◄─────────────────│  endpoint  ││
│  └────────────┘    JSON response  └───────────┘ │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│               Flask Application                  │
│                  (app.py)                         │
│                                                  │
│  1. Receives JSON: { "text": "..." }             │
│  2. Validates input                              │
│  3. Passes text to sklearn Pipeline              │
│  4. Returns prediction + probabilities           │
└─────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│           scikit-learn Pipeline                   │
│         (model/news_classifier.sav)              │
│                                                  │
│  Stage 1: TfidfVectorizer                        │
│    - English stop word removal                   │
│    - N-gram range: (1, 4)                        │
│    - IDF weighting with smoothing                │
│                                                  │
│  Stage 2: LogisticRegression                     │
│    - L2 penalty, C=1                             │
│    - Outputs: class label + class probabilities  │
└─────────────────────────────────────────────────┘
```

---

## Data Flow

### Request Flow
1. User types a news statement in the browser textarea
2. JavaScript captures the form submission and sends a `POST /analyze` request with JSON body
3. Flask validates the input and calls `model.predict()` and `model.predict_proba()`
4. The pipeline internally:
   - Tokenizes the text and computes TF-IDF features
   - Runs the feature vector through logistic regression
5. Flask returns a JSON response with the prediction and confidence
6. JavaScript renders the result with animations in the browser

### Model Loading
- The pickled sklearn Pipeline is loaded once at application startup
- If loading fails, the app enters a degraded state and returns 503 on prediction requests
- The `/health` endpoint reports the model loading status

---

## Frontend Architecture

The frontend is a single-page application built with vanilla HTML/CSS/JS (no framework dependencies):

| File | Responsibility |
|------|---------------|
| `templates/index.html` | Page structure, semantic HTML5, Jinja2 templating for static URLs |
| `static/css/style.css` | Complete styling using CSS custom properties, Grid, Flexbox, animations |
| `static/js/main.js` | Form handling, AJAX via Fetch API, DOM manipulation, scroll effects |

### Key Design Decisions
- **No frontend framework** — reduces complexity and load time
- **CSS-only animations** — no animation libraries required
- **Fetch API** — native browser API for AJAX, no jQuery dependency
- **Responsive design** — mobile-first approach with CSS media queries

---

## Model Training Summary

The model was trained through the following process:

1. **Data Preparation** — LIAR dataset statements converted to binary labels (TRUE/FALSE)
2. **Feature Extraction** — Two approaches were compared:
   - Bag of Words (CountVectorizer)
   - TF-IDF with n-grams (TfidfVectorizer)
3. **Classifier Evaluation** — Five classifiers were tested:
   - Multinomial Naive Bayes
   - Logistic Regression
   - Linear SVM
   - Stochastic Gradient Descent
   - Random Forest
4. **Hyperparameter Tuning** — GridSearchCV was used to optimize the best candidates
5. **Final Selection** — Logistic Regression with TF-IDF n-grams was chosen for its balanced performance

---

## File Structure Rationale

```
project_root/
├── app.py              → Single entry point; simple to run and deploy
├── model/              → Isolated model artifacts
├── data/               → Raw datasets, separate from code
├── templates/          → Flask template convention
├── static/             → Flask static file convention
│   ├── css/
│   └── js/
└── docs/               → All documentation in one place
```

This structure follows Flask conventions and keeps concerns separated:
- **Code** (`app.py`) is at the root for easy execution
- **Model artifacts** are in their own directory for versioning
- **Data** is isolated so it can be replaced or updated independently
- **Frontend assets** follow Flask's default static/template directories

---

## Security Considerations

- Input text is validated server-side before processing
- No user data is stored or logged
- The Flask secret key is generated randomly on each startup (configurable via environment variable)
- The model runs entirely locally — no external API calls during prediction
- Debug mode should be disabled in production

---

## Deployment Notes

For production deployment:
1. Set `debug=False` in `app.py` or use a WSGI server (Gunicorn/Waitress)
2. Set the `SECRET_KEY` environment variable
3. Consider adding rate limiting for the `/analyze` endpoint
4. Use a reverse proxy (Nginx) for static file serving in production
