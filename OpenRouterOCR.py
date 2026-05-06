"""
OpenRouter Urdu OCR Studio
==========================
Uses OpenRouter API (OpenAI-compatible) for high-accuracy Urdu OCR.
SupportsSupports Baidu Qianfan-OCR-Fast, Nemotron Nano 12B VL, Nemotron Nano Omni 30B.

pip install PyQt6 pillow pymupdf
"""

import os, sys, base64, io, json, urllib.request
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QFileDialog, QTextEdit, QFrame,
    QProgressBar, QMessageBox, QComboBox, QLineEdit,
)
from PyQt6.QtCore  import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui   import QFont, QColor, QPalette

# ── Theme ──────────────────────────────────────────────────────────────────────
BG = "#24273a"; SURFACE = "#1e2030"; OVERLAY = "#363a4f"; MUTED = "#5b6078"
TEXT = "#cad3f5"; BLUE = "#8aadf4"; LAVENDER = "#b7bdf8"; GREEN = "#a6da95"
YELLOW = "#eed49f"; RED = "#ed8796"; TEAL = "#8bd5ca"; BLACK = "#181926"

STYLE = f"""
QMainWindow,QWidget{{background:{BG};color:{TEXT};}}
QLabel{{color:{TEXT};}}
QLineEdit{{background:{OVERLAY};color:{TEXT};border:1px solid {MUTED};
    border-radius:6px;padding:5px 10px;font-size:12px;}}
QLineEdit:focus{{border:1px solid {BLUE};}}
QTextEdit{{background:{SURFACE};color:{GREEN};border:1px solid {OVERLAY};
    border-radius:8px;padding:14px;
    font-family:'Noto Nastaliq Urdu','Jameel Noori Nastaleeq','Segoe UI';
    font-size:16px;}}
QComboBox{{background:{OVERLAY};color:{TEXT};border:1px solid {MUTED};
    border-radius:6px;padding:5px 10px;min-width:240px;}}
QComboBox QAbstractItemView{{background:{OVERLAY};color:{TEXT};
    selection-background-color:{BLUE};selection-color:{BLACK};}}
QPushButton#PrimaryBtn{{background:{BLUE};color:{BLACK};border:none;
    border-radius:8px;padding:10px 24px;font-size:13px;font-weight:bold;}}
QPushButton#PrimaryBtn:hover{{background:{LAVENDER};}}
QPushButton#PrimaryBtn:disabled{{background:{OVERLAY};color:{MUTED};}}
QPushButton#SecBtn{{background:{OVERLAY};color:{TEXT};border:1px solid {MUTED};
    border-radius:6px;padding:6px 14px;font-size:11px;}}
QPushButton#SecBtn:hover{{background:{MUTED};}}
QPushButton#SaveBtn{{background:{GREEN};color:{BLACK};border:none;
    border-radius:6px;padding:6px 18px;font-size:11px;font-weight:bold;}}
QPushButton#SaveBtn:hover{{background:{TEAL};}}
QPushButton#SaveBtn:disabled{{background:{OVERLAY};color:{MUTED};}}
QProgressBar{{border:none;background:{OVERLAY};border-radius:3px;color:transparent;}}
QProgressBar::chunk{{background:{GREEN};border-radius:3px;}}
QFrame#DropZone{{background:{OVERLAY};border:2px dashed {MUTED};border-radius:14px;}}
QFrame#DropZone[drag="true"]{{background:#3e4259;border:2px solid {GREEN};}}
"""

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_API_KEY = "sk-or-v1-f637ba2e0bf65e1fb2bdbaaefc2ca0cce3315ce4a789d394a312293409df05a"

MODELS = {
    # ── Free vision models (best → fastest) ──────────────────────────────────
    "Baidu Qianfan-OCR-Fast  (free, OCR)":        "baidu/qianfan-ocr-fast:free",
    "Nemotron Nano 12B VL  (free, vision)":       "nvidia/nemotron-nano-12b-v2-vl:free",
    "Nemotron Nano Omni 30B  (free)":             "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
}

OCR_PROMPT = (
    "You are an expert Urdu/Arabic OCR engine. "
    "Transcribe ALL text visible in this image exactly as written, "
    "preserving every line break, punctuation mark, and diacritic (harakat). "
    "Output ONLY the raw transcribed text — no explanations, no commentary. "
    "CRITICAL: Do NOT hallucinate. Do NOT repeat words or lines. When you reach the end of the text in the image, STOP immediately."
)


# ── Worker ─────────────────────────────────────────────────────────────────────

class OCRWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, file_path, model_id, api_key, max_tokens=4096):
        super().__init__()
        self.file_path  = file_path
        self.model_id   = model_id
        self.api_key    = api_key
        self.max_tokens = max_tokens

    def _infer(self, pil_image) -> str:
        import time
        buf = io.BytesIO()
        pil_image.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()

        payload = {
            "model": self.model_id,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{b64}"}},
                    {"type": "text", "text": OCR_PROMPT},
                ],
            }],
            "max_tokens":        self.max_tokens,
            "temperature":       0.1,
            "top_p":             0.95,
            "frequency_penalty": 0.5,
            "presence_penalty":  0.2,
        }

        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer":  "https://urdu-ocr-studio",
            "X-Title":       "Urdu OCR Studio",
        }

        max_retries = 1
        wait = 10  # seconds; doubles each retry
        for attempt in range(max_retries + 1):
            req = urllib.request.Request(
                OPENROUTER_URL,
                data=json.dumps(payload).encode(),
                headers=headers,
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read())
                break  # success
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")
                try:
                    msg = json.loads(body).get("error", {}).get("message", body)
                except Exception:
                    msg = body

                if e.code == 429 and attempt < max_retries:
                    self.progress.emit(0, f"⏳ Rate limited — retrying in {wait}s… (attempt {attempt+1}/{max_retries})")
                    time.sleep(wait)
                    wait *= 2
                    continue

                raise RuntimeError(f"HTTP {e.code} from OpenRouter:\n{msg}")

        if "error" in data:
            raise RuntimeError(data["error"].get("message", str(data["error"])))

        return data["choices"][0]["message"]["content"].strip()

    def run(self):
        try:
            from PIL import Image
            suffix = Path(self.file_path).suffix.lower()

            if suffix == ".pdf":
                try:
                    import fitz
                except ImportError:
                    self.error.emit("PyMuPDF missing.\nRun: pip install pymupdf")
                    return

                doc, pages = fitz.open(self.file_path), []
                total = doc.page_count
                for i in range(total):
                    self.progress.emit(int(i / total * 95), f"Page {i+1}/{total} …")
                    pix = doc[i].get_pixmap(matrix=fitz.Matrix(300/72, 300/72), alpha=False)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    pages.append(f"{'─'*56}\nصفحہ {i+1}\n{'─'*56}\n{self._infer(img)}")
                doc.close()
                self.progress.emit(100, "Done!")
                self.finished.emit("\n\n".join(pages))

            elif suffix in {".jpg",".jpeg",".png",".bmp",".tiff",".tif",".webp"}:
                self.progress.emit(30, "Running OCR …")
                text = self._infer(Image.open(self.file_path).convert("RGB"))
                self.progress.emit(100, "Done!")
                self.finished.emit(text)

            else:
                self.error.emit(f"Unsupported: {suffix}")

        except Exception:
            import traceback
            self.error.emit(traceback.format_exc())


# ── Drop Frame ─────────────────────────────────────────────────────────────────

class DropZone(QFrame):
    dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)

    def _hl(self, on):
        self.setProperty("drag", "true" if on else "false")
        self.style().unpolish(self); self.style().polish(self)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept(); self._hl(True)
        else: e.ignore()

    def dragLeaveEvent(self, e): self._hl(False)

    def dropEvent(self, e):
        self._hl(False)
        if e.mimeData().urls():
            self.dropped.emit(e.mimeData().urls()[0].toLocalFile())


# ── Main Window ────────────────────────────────────────────────────────────────

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Urdu OCR Studio  —  OpenRouter")
        self.resize(960, 760)
        self.setAcceptDrops(True)
        self._worker = None
        self._build()
        self.setStyleSheet(STYLE)
        # Pre-fill saved API key
        if OPENROUTER_API_KEY:
            self.key_edit.setText(OPENROUTER_API_KEY)

    def _build(self):
        root   = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(32, 22, 32, 22)
        layout.setSpacing(14)
        self.setCentralWidget(root)

        # Title
        t = QLabel("Urdu OCR Studio")
        t.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(f"color:{BLUE};")
        layout.addWidget(t)

        s = QLabel("Powered by OpenRouter  ·  Qwen3 / Qwen2.5-VL / Gemini / GPT-4o")
        s.setFont(QFont("Segoe UI", 10))
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        s.setStyleSheet(f"color:{MUTED};")
        layout.addWidget(s)

        # API key + model row
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("API Key:"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText("sk-or-v1-…  (get free key at openrouter.ai)")
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        row1.addWidget(self.key_edit, stretch=1)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        for name, mid in MODELS.items():
            self.model_combo.addItem(name, mid)
        row2.addWidget(self.model_combo, stretch=1)
        layout.addLayout(row2)

        # Drop zone
        dz = DropZone()
        dz.dropped.connect(self._start)
        dz.setMinimumHeight(150)
        inner = QVBoxLayout(dz)
        inner.setContentsMargins(30, 20, 30, 20)

        icon = QLabel("📥")
        icon.setFont(QFont("Segoe UI", 36))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(icon)

        hint = QLabel("Drag & Drop an Image or PDF here")
        hint.setFont(QFont("Segoe UI", 13))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(hint)

        sup = QLabel("JPG · PNG · BMP · TIFF · WebP · PDF")
        sup.setFont(QFont("Segoe UI", 9))
        sup.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sup.setStyleSheet(f"color:{MUTED};")
        inner.addWidget(sup)

        self.browse_btn = QPushButton("  📂  Browse Files")
        self.browse_btn.setObjectName("PrimaryBtn")
        self.browse_btn.setMinimumHeight(40)
        self.browse_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.clicked.connect(self._browse)
        br = QHBoxLayout(); br.addStretch()
        br.addWidget(self.browse_btn); br.addStretch()
        inner.addLayout(br)
        layout.addWidget(dz)

        # Progress bar
        self.prog = QProgressBar()
        self.prog.setFixedHeight(5)
        self.prog.setTextVisible(False)
        self.prog.hide()
        layout.addWidget(self.prog)

        # Output
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        self.out.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.out.setPlaceholderText("اردو متن یہاں ظاہر ہوگا …\n(Urdu text will appear here …)")
        layout.addWidget(self.out, stretch=1)

        # Status bar
        bot = QHBoxLayout()
        self.status = QLabel("Enter your OpenRouter API key and select a file.")
        self.status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.status.setStyleSheet(f"color:{YELLOW};")
        bot.addWidget(self.status, stretch=1)

        for lbl, obj, fn in [("🗑 Clear","SecBtn",self._clear),
                               ("📋 Copy", "SecBtn",self._copy)]:
            b = QPushButton(lbl); b.setObjectName(obj)
            b.setMinimumHeight(32); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(fn); bot.addWidget(b)

        self.save_btn = QPushButton("💾 Save .txt")
        self.save_btn.setObjectName("SaveBtn")
        self.save_btn.setMinimumHeight(32)
        self.save_btn.setEnabled(False)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._save)
        bot.addWidget(self.save_btn)
        layout.addLayout(bot)

    # ── Actions ────────────────────────────────────────────────────────────────
    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Select File", "",
            "Images & PDFs (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp *.pdf)")
        if p: self._start(p)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()

    def dropEvent(self, e):
        if e.mimeData().urls():
            self._start(e.mimeData().urls()[0].toLocalFile())

    def _start(self, path):
        key = self.key_edit.text().strip()
        if not key:
            QMessageBox.warning(self, "API Key Required",
                "Paste your OpenRouter API key first.\n"
                "Get a free key at: https://openrouter.ai/keys")
            return

        self.out.clear()
        self.save_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.prog.show(); self.prog.setValue(0)
        self._set_status(f"Processing: {Path(path).name}", YELLOW)

        self._worker = OCRWorker(path, self.model_combo.currentData(), key)
        self._worker.progress.connect(
            lambda p, m: (self.prog.setValue(p), self._set_status(m, YELLOW)))
        self._worker.finished.connect(self._done)
        self._worker.error.connect(self._err)
        self._worker.start()

    def _done(self, text):
        self.prog.setValue(100)
        self.out.setPlainText(text)
        self.save_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self._set_status("✓  OCR complete!", GREEN)
        QTimer.singleShot(1500, self.prog.hide)

    def _err(self, msg):
        self.prog.hide()
        self.browse_btn.setEnabled(True)
        self.out.setPlainText(f"[ERROR]\n\n{msg}")
        self._set_status("Error — see output for details.", RED)

    def _set_status(self, msg, color=TEXT):
        self.status.setText(msg)
        self.status.setStyleSheet(f"color:{color};font-weight:bold;")

    def _clear(self):
        self.out.clear(); self.save_btn.setEnabled(False)

    def _copy(self):
        t = self.out.toPlainText()
        if t:
            QApplication.clipboard().setText(t)
            self._set_status("Copied!", TEAL)
            QTimer.singleShot(2000, lambda: self._set_status("Ready.", GREEN))

    def _save(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save", "urdu_ocr.txt", "*.txt")
        if p:
            Path(p).write_text(self.out.toPlainText(), encoding="utf-8")
            QMessageBox.information(self, "Saved", f"Saved to:\n{p}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    pal = app.palette()
    pal.setColor(QPalette.ColorRole.Window,     QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base,       QColor(SURFACE))
    pal.setColor(QPalette.ColorRole.Text,       QColor(TEXT))
    app.setPalette(pal)
    win = App()
    win.show()
    sys.exit(app.exec())
