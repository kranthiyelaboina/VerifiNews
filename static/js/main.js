/* ============================================================
   VerifiNews – Main JavaScript
   ============================================================ */

document.addEventListener("DOMContentLoaded", () => {
    const form       = document.getElementById("analysisForm");
    const textarea   = document.getElementById("newsInput");
    const charCount  = document.getElementById("charCount");
    const clearBtn   = document.getElementById("clearBtn");
    const analyzeBtn = document.getElementById("analyzeBtn");
    const btnText    = analyzeBtn.querySelector(".btn-text");
    const btnLoading = analyzeBtn.querySelector(".btn-loading");
    const resultPanel = document.getElementById("resultPanel");
    const errorPanel  = document.getElementById("errorPanel");

    // Image upload elements
    const uploadArea    = document.getElementById("uploadArea");
    const imageInput    = document.getElementById("imageInput");
    const uploadContent = document.getElementById("uploadContent");
    const uploadPreview = document.getElementById("uploadPreview");
    const previewImage  = document.getElementById("previewImage");
    const removeImageBtn = document.getElementById("removeImageBtn");
    const ocrStatus     = document.getElementById("ocrStatus");

    // Language selector
    const languageSelect = document.getElementById("languageSelect");

    // Overlay elements
    const overlay          = document.getElementById("verificationOverlay");
    const overlaySteps     = document.getElementById("overlaySteps");
    const overlayStatus    = document.getElementById("overlayStatusText");
    const overlaySpinner   = document.getElementById("overlaySpinner");
    const overlayCloseBtn  = document.getElementById("overlayCloseBtn");

    // Iframe popup elements
    const iframePopup      = document.getElementById("articleIframePopup");
    const iframeEl         = document.getElementById("articleIframe");
    const iframeLoading    = document.getElementById("iframeLoading");
    const iframeTitle      = document.getElementById("iframePopupTitle");
    const iframeCloseBtn   = document.getElementById("iframePopupClose");
    const iframeBackdrop   = iframePopup.querySelector(".iframe-popup-backdrop");
    const iframeExtLink    = document.getElementById("iframeExternalLink");

    // ---- Intro Video ----
    const introOverlay = document.getElementById("introOverlay");
    const introVideo = document.getElementById("introVideo");
    if (introOverlay && introVideo) {
        document.body.classList.add("intro-active");
        introVideo.addEventListener("ended", () => {
            introOverlay.classList.add("fade-out");
            document.body.classList.remove("intro-active");
            setTimeout(() => { introOverlay.remove(); }, 1000);
        });
        introVideo.addEventListener("error", () => {
            introOverlay.classList.add("fade-out");
            document.body.classList.remove("intro-active");
            setTimeout(() => { introOverlay.remove(); }, 1000);
        });
    }

    // ---- Character counter ----
    textarea.addEventListener("input", () => {
        charCount.textContent = textarea.value.length;
    });

    // ---- Clear button ----
    clearBtn.addEventListener("click", () => {
        textarea.value = "";
        charCount.textContent = "0";
        resultPanel.style.display = "none";
        errorPanel.style.display = "none";
        textarea.focus();
    });

    // ---- Navbar scroll effect ----
    const navbar = document.querySelector(".navbar");
    window.addEventListener("scroll", () => {
        navbar.classList.toggle("scrolled", window.scrollY > 10);
    });

    // ---- Image Upload ----
    uploadArea.addEventListener("click", (e) => {
        if (e.target.closest("#removeImageBtn")) return;
        imageInput.click();
    });

    uploadArea.addEventListener("dragover", (e) => {
        e.preventDefault();
        uploadArea.classList.add("drag-over");
    });

    uploadArea.addEventListener("dragleave", () => {
        uploadArea.classList.remove("drag-over");
    });

    uploadArea.addEventListener("drop", (e) => {
        e.preventDefault();
        uploadArea.classList.remove("drag-over");
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith("image/")) {
            handleImageFile(file);
        }
    });

    imageInput.addEventListener("change", () => {
        if (imageInput.files[0]) {
            handleImageFile(imageInput.files[0]);
        }
    });

    removeImageBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        imageInput.value = "";
        uploadContent.style.display = "flex";
        uploadPreview.style.display = "none";
        previewImage.src = "";
    });

    async function handleImageFile(file) {
        // Show preview
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImage.src = e.target.result;
            uploadContent.style.display = "none";
            uploadPreview.style.display = "block";
        };
        reader.readAsDataURL(file);

        // Show overlay immediately for OCR extraction
        showOverlay("Extracting Text", "Reading text from your image...");
        errorPanel.style.display = "none";

        try {
            const formData = new FormData();
            formData.append("image", file);
            formData.append("language", languageSelect.value);

            const response = await fetch("/ocr", {
                method: "POST",
                body: formData,
            });

            const data = await response.json();

            if (!response.ok) {
                hideOverlay();
                showError(data.error || "Failed to extract text from image.");
                return;
            }

            // Set extracted text in textarea
            textarea.value = data.text;
            charCount.textContent = data.text.length;

            // Transition overlay to analysis phase
            updateOverlayStatus("Text extracted. Starting verification pipeline...");
            await delay(600);

            // Run analysis within the already-open overlay
            runAnalysis(true);
        } catch (err) {
            hideOverlay();
            showError("Failed to process image. Please ensure the server is running.");
        }
    }

    // ---- Form submission (button is outside form, use click) ----
    analyzeBtn.addEventListener("click", (e) => {
        e.preventDefault();
        runAnalysis();
    });

    // Also allow Enter in form to trigger
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        runAnalysis();
    });

    // ---- Core analysis function ----
    async function runAnalysis(overlayAlreadyOpen) {
        const text = textarea.value.trim();
        if (!text) {
            showError("Please enter a news statement to analyze.");
            return;
        }

        // Show overlay with blur (unless already open from OCR flow)
        if (!overlayAlreadyOpen) {
            showOverlay("Verification Pipeline", "Initializing verification pipeline...");
        }
        setLoading(true);
        resultPanel.style.display = "none";
        errorPanel.style.display = "none";

        try {
            const response = await fetch("/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text, language: languageSelect.value }),
            });

            const data = await response.json();

            if (!response.ok) {
                hideOverlay();
                showError(data.error || "Something went wrong. Please try again.");
                return;
            }

            // Reveal steps one-by-one in the overlay, then show result
            await revealStepsInOverlay(data);
            displayResult(data);
        } catch (err) {
            hideOverlay();
            showError("Unable to connect to the server. Please ensure the server is running.");
        } finally {
            setLoading(false);
        }
    }

    // ---- Overlay helpers ----
    const overlayShield = document.getElementById("overlayShield");
    const overlayTitle  = document.getElementById("overlayTitle");

    function showOverlay(title, status) {
        overlaySteps.innerHTML = "";
        overlayTitle.textContent = title || "Verification Pipeline";
        overlayStatus.textContent = status || "Initializing verification pipeline...";
        overlayStatus.className = "overlay-status-text";
        overlaySpinner.style.display = "block";
        overlayCloseBtn.style.display = "none";
        overlayShield.classList.remove("done");
        overlay.classList.add("active");
        document.body.classList.add("overlay-active");
    }

    function hideOverlay() {
        overlay.classList.remove("active");
        document.body.classList.remove("overlay-active");
    }

    function updateOverlayStatus(text) {
        overlayStatus.textContent = text;
    }

    overlayCloseBtn.addEventListener("click", () => {
        hideOverlay();
        resultPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });

    async function revealStepsInOverlay(data) {
        const steps = data.analysis_steps || [];
        const checkIcon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>';
        const skipIcon = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';

        for (let i = 0; i < steps.length; i++) {
            const step = steps[i];
            overlayStatus.textContent = step.step + "...";

            // Wait before revealing each step
            await delay(700);

            const stepEl = document.createElement("div");
            stepEl.className = `overlay-step-item ${step.status}`;
            const icon = step.status === "complete" ? checkIcon : skipIcon;
            stepEl.innerHTML = `
                <div class="overlay-step-icon ${step.status}">${icon}</div>
                <div class="overlay-step-content">
                    <span class="overlay-step-title">${escapeHtml(step.step)}</span>
                    <span class="overlay-step-detail">${escapeHtml(step.detail)}</span>
                </div>
            `;
            overlaySteps.appendChild(stepEl);
        }

        // Final verdict reveal
        await delay(500);
        const isReal = data.is_real;
        overlayTitle.textContent = isReal ? "Verified" : "Alert";
        overlayStatus.textContent = isReal
            ? "This statement appears to be authentic."
            : "This statement appears to be unreliable.";
        overlayStatus.className = `overlay-status-text ${isReal ? "verdict-real" : "verdict-fake"}`;
        overlaySpinner.style.display = "none";
        overlayShield.classList.add("done");
        overlayCloseBtn.style.display = "inline-flex";
    }

    function delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ---- Display result ----
    function displayResult(data) {
        const isReal = data.is_real;
        const cls = isReal ? "real" : "fake";

        // --- Analysis Steps (Inner Workings) ---
        const stepsContainer = document.getElementById("stepsContainer");
        stepsContainer.innerHTML = "";
        if (data.analysis_steps && data.analysis_steps.length > 0) {
            data.analysis_steps.forEach((step, index) => {
                const stepEl = document.createElement("div");
                stepEl.className = `step-item ${step.status}`;
                stepEl.style.animationDelay = `${index * 0.15}s`;

                const statusIcon = step.status === "complete"
                    ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
                    : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';

                stepEl.innerHTML = `
                    <div class="step-item-icon ${step.status}">${statusIcon}</div>
                    <div class="step-item-content">
                        <span class="step-item-title">${escapeHtml(step.step)}</span>
                        <span class="step-item-detail">${escapeHtml(step.detail)}</span>
                    </div>
                `;
                stepsContainer.appendChild(stepEl);
            });
            document.getElementById("analysisSteps").style.display = "block";
        }

        // Icon
        const iconEl = document.getElementById("resultIcon");
        iconEl.className = "result-icon " + cls;
        iconEl.innerHTML = isReal
            ? '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>'
            : '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';

        // Verdict
        const verdictEl = document.getElementById("resultVerdict");
        verdictEl.className = "result-verdict " + cls;
        verdictEl.textContent = isReal
            ? "This Statement Appears Authentic"
            : "This Statement Appears Unreliable";

        // Subtitle
        document.getElementById("resultSubtitle").textContent =
            `Multi-source verification classified this as ${data.prediction} with ${data.confidence}% confidence.`;

        // Confidence bar
        document.getElementById("confidenceValue").textContent = data.confidence + "%";
        const fill = document.getElementById("confidenceFill");
        fill.className = "confidence-fill " + cls;
        fill.style.width = "0";
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                fill.style.width = data.confidence + "%";
            });
        });

        // Probabilities
        document.getElementById("truthProb").textContent = data.truth_probability + "%";
        document.getElementById("fakeProb").textContent = data.fake_probability + "%";

        // Analysis Insight (Gemini reason)
        const reasonPanel = document.getElementById("reasonPanel");
        if (data.gemini_reason) {
            document.getElementById("reasonText").textContent = data.gemini_reason;
            reasonPanel.style.display = "block";
        } else {
            reasonPanel.style.display = "none";
        }

        // Related News Articles
        const articlesPanel = document.getElementById("newsArticlesPanel");
        const articlesList = document.getElementById("articlesList");
        if (data.news_articles && data.news_articles.length > 0) {
            articlesList.innerHTML = "";
            data.news_articles.forEach((article) => {
                const articleEl = document.createElement("a");
                articleEl.className = "article-item";
                articleEl.href = article.url;
                articleEl.addEventListener("click", (e) => {
                    e.preventDefault();
                    openArticlePopup(article.url, article.title);
                });
                articleEl.innerHTML = `
                    <div class="article-source">${escapeHtml(article.source)}</div>
                    <div class="article-title">${escapeHtml(article.title)}</div>
                    <div class="article-relevance">Relevance: ${article.relevance}%</div>
                `;
                articlesList.appendChild(articleEl);
            });
            articlesPanel.style.display = "block";
        } else {
            articlesPanel.style.display = "none";
        }

        // Google Search Grounding Sources
        const groundingPanel = document.getElementById("groundingSourcesPanel");
        const groundingList = document.getElementById("groundingSourcesList");
        if (data.grounding_sources && data.grounding_sources.length > 0) {
            groundingList.innerHTML = "";
            data.grounding_sources.forEach((source) => {
                const sourceEl = document.createElement("a");
                sourceEl.className = "article-item";
                sourceEl.href = source.url;
                sourceEl.addEventListener("click", (e) => {
                    e.preventDefault();
                    openArticlePopup(source.url, source.title || "Google Search Source");
                });
                let domain = 'Web Source';
                try { domain = new URL(source.url).hostname.replace(/^www\./, ''); } catch(e) {}
                sourceEl.innerHTML = `
                    <div class="article-source">${escapeHtml(domain)}</div>
                    <div class="article-title">${escapeHtml(source.title || source.url)}</div>
                `;
                groundingList.appendChild(sourceEl);
            });
            groundingPanel.style.display = "block";
        } else {
            groundingPanel.style.display = "none";
        }

        // Show panel
        resultPanel.style.display = "block";

        // Auto-play TTS for the analysis insight
        if (data.gemini_reason) {
            playTTS(data.gemini_reason);
        }
    }

    // ---- Escape HTML to prevent XSS ----
    function escapeHtml(str) {
        const div = document.createElement("div");
        div.appendChild(document.createTextNode(str || ""));
        return div.innerHTML;
    }

    // ---- Show error ----
    function showError(message) {
        document.getElementById("errorMessage").textContent = message;
        errorPanel.style.display = "block";
    }

    // ---- TTS (Deepgram) ----
    const ttsBtn     = document.getElementById("ttsBtn");
    const ttsAudio   = document.getElementById("ttsAudio");
    const ttsIconPlay = ttsBtn.querySelector(".tts-icon-play");
    const ttsIconStop = ttsBtn.querySelector(".tts-icon-stop");
    const ttsBtnSpinner = ttsBtn.querySelector(".tts-spinner");
    let ttsLoading = false;

    function setTTSState(state) {
        // state: "idle" | "loading" | "playing"
        ttsIconPlay.style.display  = state === "idle" ? "" : "none";
        ttsIconStop.style.display  = state === "playing" ? "" : "none";
        ttsBtnSpinner.style.display = state === "loading" ? "" : "none";
        ttsBtn.classList.toggle("playing", state === "playing");
    }

    async function playTTS(text) {
        if (ttsLoading) return;
        // Stop any current playback
        ttsAudio.pause();
        ttsAudio.removeAttribute("src");

        ttsLoading = true;
        setTTSState("loading");

        try {
            const resp = await fetch("/tts", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text }),
            });
            if (!resp.ok) {
                setTTSState("idle");
                ttsLoading = false;
                return;
            }
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            ttsAudio.src = url;
            ttsAudio.play();
            setTTSState("playing");
        } catch {
            setTTSState("idle");
        }
        ttsLoading = false;
    }

    ttsAudio.addEventListener("ended", () => setTTSState("idle"));
    ttsAudio.addEventListener("pause", () => {
        if (ttsAudio.ended || ttsAudio.currentTime === 0) setTTSState("idle");
    });

    ttsBtn.addEventListener("click", () => {
        if (!ttsAudio.paused) {
            ttsAudio.pause();
            ttsAudio.currentTime = 0;
            setTTSState("idle");
            return;
        }
        const reasonText = document.getElementById("reasonText").textContent;
        if (reasonText) playTTS(reasonText);
    });

    // ---- Loading state ----
    function setLoading(loading) {
        analyzeBtn.disabled = loading;
        const sparkleSvg = analyzeBtn.querySelector(".sparkle");
        btnText.style.display = loading ? "none" : "inline-flex";
        if (sparkleSvg) sparkleSvg.style.display = loading ? "none" : "";
        btnLoading.style.display = loading ? "inline-flex" : "none";
    }

    // ---- Article Iframe Popup ----
    function openArticlePopup(url, title) {
        iframeTitle.textContent = title || "Loading article...";
        iframeExtLink.href = url;
        iframeLoading.classList.remove("hidden");
        iframeEl.src = "";
        iframePopup.classList.add("active");
        document.body.style.overflow = "hidden";

        // Load the URL in iframe
        iframeEl.src = url;
        iframeEl.onload = () => {
            iframeLoading.classList.add("hidden");
        };
        // Fallback: hide loading after timeout in case onload doesn't fire
        setTimeout(() => { iframeLoading.classList.add("hidden"); }, 5000);
    }

    function closeArticlePopup() {
        iframePopup.classList.remove("active");
        document.body.style.overflow = "";
        // Fully unload iframe to stop any audio/video
        setTimeout(() => { iframeEl.src = ""; }, 300);
    }

    iframeCloseBtn.addEventListener("click", closeArticlePopup);
    iframeBackdrop.addEventListener("click", closeArticlePopup);
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && iframePopup.classList.contains("active")) {
            closeArticlePopup();
        }
    });
});
