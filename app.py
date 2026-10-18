from flask import Flask, request, jsonify, render_template_string
from pypdf import PdfReader
import os
import time
import io

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

app = Flask(__name__)

pdf_text = ""
pdf_name = "No PDF loaded"
groq_client = None

api_key = os.getenv("GROQ_API_KEY", "")
if api_key and GROQ_AVAILABLE:
    groq_client = Groq(api_key=api_key)

# ---------- HTML (Mobile First PWA) ----------
HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="theme-color" content="#1e1e2e">
    <meta name="description" content="G3Q Quiz Helper - Fast PDF answers">
    <link rel="manifest" href="/manifest.json">
    <title>G3Q Helper</title>

    <script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>

    <style>
        :root {
            --bg: #0f0f14;
            --panel: #1a1a24;
            --text: #e4e4f0;
            --muted: #9a9ab0;
            --input: #2a2a3a;
            --border: #3a3a4a;
            --accent: #7c9cff;
            --green: #4ade80;
            --orange: #fb923c;
            --danger: #f87171;
        }
        [data-theme="light"] {
            --bg: #f4f4f8;
            --panel: #ffffff;
            --text: #1a1a24;
            --muted: #666680;
            --input: #f0f0f5;
            --border: #d0d0e0;
            --accent: #3b82f6;
            --green: #16a34a;
            --orange: #ea580c;
            --danger: #dc2626;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
            background: var(--bg);
            color: var(--text);
            min-height: 100vh;
            min-height: 100dvh;
            padding: 12px;
            padding-bottom: 24px;
            transition: background 0.25s, color 0.25s;
        }

        .app {
            max-width: 480px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 4px 0;
        }
        h1 {
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--accent);
        }
        .theme-btn {
            width: 40px; height: 40px;
            border-radius: 50%;
            border: 1px solid var(--border);
            background: var(--input);
            font-size: 1.2rem;
            display: flex; align-items: center; justify-content: center;
        }

        .card {
            background: var(--panel);
            border-radius: 16px;
            padding: 14px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }

        .pdf-info {
            font-size: 0.8rem;
            color: var(--muted);
            text-align: center;
            margin-bottom: 10px;
            word-break: break-all;
        }

        .btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s, opacity 0.15s;
        }
        .btn:active { transform: scale(0.97); }
        .btn:disabled { opacity: 0.5; }

        .btn-primary { background: var(--accent); color: white; }
        .btn-green { background: var(--green); color: white; }
        .btn-orange { background: var(--orange); color: white; }
        .btn-outline {
            background: transparent;
            border: 1.5px solid var(--border);
            color: var(--text);
        }

        .btn-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }

        label {
            font-size: 0.8rem;
            color: var(--muted);
            margin-bottom: 6px;
            display: block;
        }

        textarea, .answer-box {
            width: 100%;
            background: var(--input);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px;
            font-size: 0.95rem;
            line-height: 1.4;
        }
        textarea {
            min-height: 90px;
            resize: vertical;
        }
        textarea:focus { outline: none; border-color: var(--accent); }

        .answer-box {
            min-height: 110px;
            white-space: pre-wrap;
            overflow-y: auto;
        }

        .status {
            text-align: center;
            font-size: 0.78rem;
            color: var(--muted);
            padding: 4px 0;
        }

        .hint {
            font-size: 0.75rem;
            color: var(--muted);
            text-align: center;
            line-height: 1.4;
            padding: 0 8px;
        }

        input[type="file"] { display: none; }

        /* Camera preview */
        #cameraPreview {
            display: none;
            width: 100%;
            border-radius: 12px;
            margin-bottom: 10px;
            background: #000;
        }
        #cameraPreview.active { display: block; }

        .install-banner {
            display: none;
            background: var(--accent);
            color: white;
            padding: 12px 16px;
            border-radius: 12px;
            text-align: center;
            font-size: 0.9rem;
            font-weight: 600;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <div class="app">
        <div class="header">
            <h1>G3Q Helper</h1>
            <button class="theme-btn" id="themeBtn">🌙</button>
        </div>

        <div class="install-banner" id="installBanner">
            📲 Install App on Home Screen
        </div>

        <div class="card">
            <div class="pdf-info" id="pdfInfo">No PDF loaded</div>

            <label class="btn btn-primary" style="margin-bottom:10px;">
                📄 Upload PDF
                <input type="file" id="pdfInput" accept="application/pdf">
            </label>

            <div class="btn-row" style="margin-bottom:10px;">
                <button class="btn btn-orange" id="cameraBtn" onclick="startCamera()">📷 Camera</button>
                <button class="btn btn-outline" id="galleryBtn" onclick="document.getElementById('galleryInput').click()">🖼️ Gallery</button>
                <input type="file" id="galleryInput" accept="image/*" capture="environment" style="display:none">
            </div>

            <video id="cameraPreview" playsinline autoplay muted></video>
            <button class="btn btn-green" id="snapBtn" style="display:none; margin-bottom:10px;" onclick="snapPhoto()">
                ⚡ Snap & Get Answer
            </button>
            <button class="btn btn-outline" id="stopCamBtn" style="display:none; margin-bottom:10px;" onclick="stopCamera()">
                Stop Camera
            </button>
        </div>

        <div class="card">
            <label>Question</label>
            <textarea id="question" placeholder="Type, paste, or capture the question..."></textarea>

            <button class="btn btn-green" id="askBtn" style="margin-top:12px;" onclick="ask()">
                Get Answer
            </button>
        </div>

        <div class="card">
            <label>Answer</label>
            <div class="answer-box" id="answer">Waiting for question...</div>
        </div>

        <div class="status" id="status">Ready</div>
        <div class="hint">
            Best way: Upload PDF once → Take photo of question with Camera → Answer appears automatically
        </div>
    </div>

    <script>
        // ========== Theme ==========
        const themeBtn = document.getElementById('themeBtn');
        const html = document.documentElement;
        const savedTheme = localStorage.getItem('g3q-theme') || 'dark';
        html.setAttribute('data-theme', savedTheme);
        themeBtn.textContent = savedTheme === 'dark' ? '🌙' : '☀️';

        themeBtn.onclick = () => {
            const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            html.setAttribute('data-theme', next);
            localStorage.setItem('g3q-theme', next);
            themeBtn.textContent = next === 'dark' ? '🌙' : '☀️';
            document.querySelector('meta[name="theme-color"]').content = next === 'dark' ? '#1e1e2e' : '#f4f4f8';
        };

        // ========== Elements ==========
        const pdfInput = document.getElementById('pdfInput');
        const pdfInfo = document.getElementById('pdfInfo');
        const questionEl = document.getElementById('question');
        const answerEl = document.getElementById('answer');
        const statusEl = document.getElementById('status');
        const askBtn = document.getElementById('askBtn');
        const cameraBtn = document.getElementById('cameraBtn');
        const snapBtn = document.getElementById('snapBtn');
        const stopCamBtn = document.getElementById('stopCamBtn');
        const preview = document.getElementById('cameraPreview');
        const galleryInput = document.getElementById('galleryInput');

        let stream = null;
        let worker = null;

        // Preload OCR
        (async () => {
            try {
                worker = await Tesseract.createWorker('eng', 1, { logger: () => {} });
                await worker.setParameters({
                    tessedit_pageseg_mode: '6',
                    tessedit_ocr_engine_mode: '1'
                });
                statusEl.textContent = "Ready • OCR loaded";
            } catch(e) {
                statusEl.textContent = "Ready";
            }
        })();

        // ========== PDF Upload ==========
        pdfInput.addEventListener('change', async () => {
            const file = pdfInput.files[0];
            if (!file) return;
            statusEl.textContent = "Uploading PDF...";
            const fd = new FormData();
            fd.append('pdf', file);
            try {
                const res = await fetch('/upload', { method: 'POST', body: fd });
                const data = await res.json();
                if (data.error) throw new Error(data.error);
                pdfInfo.textContent = `✅ ${data.name} (${data.pages} pages)`;
                statusEl.textContent = "PDF ready";
            } catch (err) {
                statusEl.textContent = "Upload failed";
                alert(err.message);
            }
        });

        // ========== Camera ==========
        async function startCamera() {
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
                    audio: false
                });
                preview.srcObject = stream;
                preview.classList.add('active');
                snapBtn.style.display = 'flex';
                stopCamBtn.style.display = 'flex';
                cameraBtn.style.display = 'none';
                statusEl.textContent = "Camera ready • Point at question";
            } catch (err) {
                alert("Camera permission denied or not available");
            }
        }

        function stopCamera() {
            if (stream) {
                stream.getTracks().forEach(t => t.stop());
                stream = null;
            }
            preview.srcObject = null;
            preview.classList.remove('active');
            snapBtn.style.display = 'none';
            stopCamBtn.style.display = 'none';
            cameraBtn.style.display = 'flex';
            statusEl.textContent = "Camera stopped";
        }

        // Snap photo → OCR → Answer
        async function snapPhoto() {
            if (!stream) return;
            snapBtn.disabled = true;
            statusEl.textContent = "Capturing...";

            const canvas = document.createElement('canvas');
            canvas.width = preview.videoWidth;
            canvas.height = preview.videoHeight;
            canvas.getContext('2d').drawImage(preview, 0, 0);

            await processImage(canvas);
            snapBtn.disabled = false;
        }

        // Gallery image
        galleryInput.addEventListener('change', async () => {
            const file = galleryInput.files[0];
            if (!file) return;
            statusEl.textContent = "Processing image...";
            const img = new Image();
            img.onload = async () => {
                const canvas = document.createElement('canvas');
                canvas.width = img.width;
                canvas.height = img.height;
                canvas.getContext('2d').drawImage(img, 0, 0);
                await processImage(canvas);
            };
            img.src = URL.createObjectURL(file);
        });

        // Common image processing
        async function processImage(canvas) {
            const start = performance.now();
            statusEl.textContent = "Reading text (OCR)...";

            try {
                if (!worker) {
                    worker = await Tesseract.createWorker('eng', 1);
                    await worker.setParameters({
                        tessedit_pageseg_mode: '6',
                        tessedit_ocr_engine_mode: '1'
                    });
                }

                // Resize if too large
                let processCanvas = canvas;
                if (canvas.width > 1400) {
                    const scale = 1400 / canvas.width;
                    processCanvas = document.createElement('canvas');
                    processCanvas.width = 1400;
                    processCanvas.height = canvas.height * scale;
                    processCanvas.getContext('2d').drawImage(canvas, 0, 0, processCanvas.width, processCanvas.height);
                }

                const { data: { text } } = await worker.recognize(processCanvas);
                const cleaned = text.replace(/\s+/g, ' ').trim();

                if (!cleaned || cleaned.length < 8) {
                    throw new Error("Could not read clear text. Try better lighting or closer photo.");
                }

                questionEl.value = cleaned;
                statusEl.textContent = `OCR done • Getting answer...`;
                await ask(true, start);
            } catch (err) {
                answerEl.textContent = err.message;
                statusEl.textContent = "OCR failed";
            }
        }

        // ========== Ask ==========
        async function ask(fromCamera = false, startTime = null) {
            const question = questionEl.value.trim();
            if (!question) {
                alert("Please enter or capture a question");
                return;
            }

            askBtn.disabled = true;
            if (!fromCamera) {
                askBtn.textContent = "Thinking...";
                statusEl.textContent = "Processing...";
            }
            if (!startTime) startTime = performance.now();

            try {
                const res = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question })
                });
                const data = await res.json();
                if (data.error) throw new Error(data.error);

                const total = ((performance.now() - startTime) / 1000).toFixed(1);
                answerEl.textContent = data.answer;
                statusEl.textContent = `${data.mode} • ${total}s`;
            } catch (err) {
                answerEl.textContent = "Error: " + err.message;
                statusEl.textContent = "Error";
            } finally {
                askBtn.disabled = false;
                askBtn.textContent = "Get Answer";
            }
        }

        // ========== PWA Install ==========
        let deferredPrompt;
        const installBanner = document.getElementById('installBanner');

        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            installBanner.style.display = 'block';
        });

        installBanner.addEventListener('click', async () => {
            if (!deferredPrompt) return;
            deferredPrompt.prompt();
            const { outcome } = await deferredPrompt.userChoice;
            if (outcome === 'accepted') {
                installBanner.style.display = 'none';
            }
            deferredPrompt = null;
        });
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "G3Q Helper",
        "short_name": "G3Q",
        "description": "Fast PDF quiz answers for G3Q",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f0f14",
        "theme_color": "#1e1e2e",
        "orientation": "portrait",
        "icons": [
            {
                "src": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f4d1.png",
                "sizes": "72x72",
                "type": "image/png"
            },
            {
                "src": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f4d1.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f4d1.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

@app.route("/upload", methods=["POST"])
def upload():
    global pdf_text, pdf_name
    if "pdf" not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files["pdf"]
    try:
        reader = PdfReader(io.BytesIO(file.read()))
        text = "".join((p.extract_text() or "") + "\n\n" for p in reader.pages)
        pdf_text = text.strip()
        pdf_name = file.filename
        return jsonify({
            "name": pdf_name,
            "chars": len(pdf_text),
            "pages": len(reader.pages)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/ask", methods=["POST"])
def ask():
    global pdf_text, groq_client
    data = request.get_json()
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Empty question"}), 400
    if not pdf_text:
        return jsonify({"error": "No PDF loaded"}), 400

    try:
        if groq_client:
            answer = ask_groq(question)
            mode = "Groq"
        else:
            answer = local_search(question)
            mode = "Local"
        return jsonify({"answer": answer, "mode": mode})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def ask_groq(question):
    context = pdf_text[:28000]
    prompt = f"""You are a precise G3Q (Gujarat Gyan Guru Quiz) assistant.
Answer using ONLY the PDF text.
Give the shortest correct answer (name, number, year, scheme name etc.).
If not found, say "Not found in PDF".

PDF:
{context}

Question: {question}

Answer:"""
    resp = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.05,
        max_tokens=120,
    )
    return resp.choices[0].message.content.strip()

def local_search(question):
    q = question.lower()
    kws = [w for w in q.split() if len(w) > 3]
    sents = []
    for para in pdf_text.split("\n"):
        for s in para.replace("?", ".").replace("!", ".").split("."):
            s = s.strip()
            if len(s) > 20:
                sents.append(s)
    scored = [(sum(1 for k in kws if k in s.lower()), s) for s in sents]
    scored = [x for x in scored if x[0] > 0]
    if not scored:
        return "No matching text found."
    scored.sort(reverse=True)
    return "\n\n".join(s for _, s in scored[:3])

if __name__ == "__main__":
    print("\n📱 G3Q Mobile App running!")
    print("→ On your phone open: http://YOUR_COMPUTER_IP:5000")
    print("→ Or use localhost if testing in mobile browser\n")
    app.run(host="0.0.0.0", port=5000, debug=False)
