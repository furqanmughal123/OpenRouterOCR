# OpenRouter OCR Studio

A desktop GUI application for high-accuracy Optical Character Recognition (OCR) powered by the OpenRouter API. Built with Python and PyQt6, this tool allows you to easily extract text from images and PDF documents, particularly excelling at complex scripts like Urdu (Nastaliq) and Arabic.

## Features

- **Modern GUI**: Clean, dark-themed user interface with drag-and-drop support.
- **Multiple AI Models**: Choose between free vision and OCR models available via OpenRouter:
  - Baidu Qianfan-OCR-Fast (Best for general OCR)
  - Nemotron Nano 12B VL
  - Nemotron Nano Omni 30B
- **PDF Support**: Process multi-page PDF documents effortlessly.
- **Image Support**: Works with standard image formats (JPG, PNG, BMP, TIFF, WebP).
- **Export Options**: Copy text to clipboard or save directly as `.txt` or `.pdf`.
- **RTL Language Support**: Text box natively optimized for Right-to-Left (RTL) languages like Urdu and Arabic.

## Prerequisites

Make sure you have Python installed. You can install the required dependencies using the provided `requirements.txt` file.

```bash
pip install -r requirements.txt
```

*Dependencies include: `PyQt6`, `pillow`, `pymupdf`*

## Getting an API Key

To use this application, you need an API key from OpenRouter.

1. Go to the OpenRouter website: [https://openrouter.ai/](https://openrouter.ai/)
2. Create an account or log in.
3. Generate a new API key from your account dashboard.
4. (Optional) You can paste the key directly into the application, or replace the default key on line 58 of `OpenRouterOCR.py` to pre-fill it automatically every time you launch the app.

## Usage

1. Run the application:
   ```bash
   python OpenRouterOCR.py
   ```
   *Alternatively, you can just double-click the `OpenRouterOCR.bat` file if you are on Windows.*
2. Paste your OpenRouter API key into the "API Key" field (if not pre-filled).
3. Select your preferred model from the dropdown menu.
4. Drag and drop an image or PDF into the drop zone, or click "Browse Files" to select a file manually.
5. Wait for the OCR process to complete. The progress bar will indicate the status.
6. Review the extracted text. You can copy it to the clipboard or click "Save" to export it as a text file or PDF.
