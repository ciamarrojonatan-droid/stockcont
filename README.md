# StockCont 📈🤖

> **Automated pipeline for AI stock asset generation, trend analysis, and cataloging.**

StockCont is an end-to-end automation system designed to analyze market trends in microstock platforms (such as Adobe Stock), reverse-engineer visual aesthetics using Multimodal LLMs, and autonomously generate and catalog commercial-grade AI assets for passive income.

---

## 🏗️ Architecture & Pipeline

The system is designed as a 4-phase data pipeline:

### 1. The "Scout" (Trend Analyzer)
* **Module**: `src/scraper/adobe_stock.py`
* **Function**: Uses Playwright to scrape top-trending assets on Adobe Stock. It downloads reference images and compiles metadata into a structured raw JSON dataset (`data/raw/trends.json`).

### 2. The "Art Director" (Prompt Engineering)
* **Module**: `src/analyzer/director.py`
* **Function**: Leverages Google Gemini (1.5/3.8 Flash Vision) to analyze the "visual DNA" of trending images (lighting, composition, style, color palette). It generates highly commercial derivative prompts optimized for AI generators (Midjourney/ComfyUI), saving them to `data/processed/prompts.json`.

### 3. The "Factory" (Mass Generation)
* **Module**: `src/factory/runninghub_bot.py`
* **Function**: An RPA (Robotic Process Automation) hybrid bot using Playwright. It automatically injects the batch prompts into a Runninghub (ComfyUI) workflow, handles pop-ups, and downloads the final upscaled images autonomously.

### 4. The "Cataloger" (Metadata & SEO) *[WIP]*
* **Module**: *Pending*
* **Function**: Will use computer vision to analyze the final generated assets and produce a formatted CSV containing SEO-optimized titles and 50 target keywords per image, ready for Adobe Stock bulk upload.

---

## 🚀 Technology Stack

* **Language**: Python 3.11+
* **Web Automation**: Playwright (Sync API)
* **LLM Integration**: Google Generative AI SDK (Gemini Vision)
* **Network & Data**: HTTPX, Pillow, JSON
* **Testing**: Pytest

---

## ⚙️ Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ciamarrojonatan-droid/stockcont.git
   cd stockcont
   ```

2. **Set up the Python Virtual Environment**:
   ```bash
   python -m venv venv
   
   # Windows
   .\venv\Scripts\activate
   
   # Linux/macOS
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   npm install
   ```

4. **Install Playwright Browsers**:
   ```bash
   playwright install chromium
   ```

5. **Environment Variables**:
   Create a `.env` file in the root directory (or export directly) with your Gemini API key:
   ```env
   GEMINI_API_KEY="your_google_gemini_api_key_here"
   ```

---

## 💻 Usage

Execute the pipeline phases sequentially:

**Phase 1: Run the Scraper**
```bash
python src/scraper/adobe_stock.py
```
*(Scrapes Adobe Stock and saves images to `data/raw/images/` and metadata to `data/raw/trends.json`)*

**Phase 2: Run the Art Director**
```bash
python src/analyzer/director.py
```
*(Analyzes images and generates prompts in `data/processed/prompts.json`)*

**Phase 3: Run the Factory Bot**
```bash
python src/factory/runninghub_bot.py
```
*(Automates image generation via Runninghub)*

---

## 🛣️ Roadmap
- [x] Trend scraping and image extraction.
- [x] Vision-based visual DNA reverse engineering.
- [x] RPA integration with Runninghub.
- [ ] Automated upscaling validation.
- [ ] Phase 4: Automated keyword and title generation for microstock CSV upload.

## 📄 License
MIT License
