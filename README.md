# Room Change Detector

A browser-based tool that analyzes before-and-after photographs of a room or desk area and produces a structured change report with paired image-region evidence. No manual labelling required.

## Features

- **Drag-and-drop upload** for before/after photo sets (up to 3 images each)
- **Two-pass Gemini 3.6 Flash analysis**: scene assessment → object-level change detection
- **Evidence crops**: side-by-side before/after image regions for each detected change
- **False positive prevention**: lighting/exposure changes are not reported as physical changes
- **Not-verifiable handling**: objects hidden or out of frame are flagged as "not verifiable" (not "removed")
- **Uncertain matches**: shown separately with suggestions for useful extra angles
- **Demo Mode**: 1-click loading of generated demo images directly in the browser
- **Cost tracking**: tokens used and estimated cost per analysis

## Quick Start

### Prerequisites
- Python 3.11+
- A Google Gemini API key (Get a free one at https://aistudio.google.com/apikey)

### Setup & Usage

1. Create a `.env` file in the root folder (next to `start.bat`) and add your key:
   ```env
   GEMINI_API_KEY=your_key_here
   ```
2. Double-click `start.bat`. It will automatically install dependencies and start the server.
3. Open `http://localhost:8000` in your browser.
4. Click **Load Demo Data** to test with auto-generated images, or upload your own photos.
5. Click **Analyze Changes** to view the report.

*(Manual setup: `pip install -r backend/requirements.txt`, run `python test_sets/generate_test_set.py`, then `uvicorn backend.app:app --port 8000`)*

## Project Structure

```text
├── backend/
│   ├── app.py              # FastAPI server
│   ├── analyzer.py          # Two-pass Gemini analysis engine
│   ├── models.py            # Pydantic data models
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html           # Single-page app
│   ├── style.css            # Responsive styling
│   └── app.js               # Upload handling & result rendering
├── test_sets/
│   ├── generate_test_set.py # Synthetic test image generator
│   ├── expected_results.json# Ground truth (recorded before testing)
│   └── run_tests.py         # Automated test runner
├── .env                     # API Key (not tracked in Git)
├── .gitignore
├── start.bat                # 1-click Windows launcher
├── README.md
└── delivery_notes.md
```

## Test Sets

Three reproducible test scenarios (generated via `generate_test_set.py`):

| Set | Description | Expected Outcome |
|-----|-------------|-----------------|
| Set 1 | Normal changes: mug moved, sticky notes added, phone hidden | Detect move + add; phone = not_verifiable |
| Set 2 | No changes, different lighting | Zero physical changes detected |
| Set 3 | Cropped after view | Mug & phone = not_verifiable; book & pencils = unchanged |

Run automated tests:
```bash
cd test_sets
python run_tests.py
```

## AI Tools & Models

- **Gemini 3.6 Flash** (Google): Vision-based image analysis via `google-genai` SDK. Chosen for superior speed and native structured JSON output.
- **Pillow**: Image cropping for evidence regions
- **FastAPI**: HTTP server

## Cost Estimates

Per before/after analysis (1 image each, 800×600):
- ~2 API calls
- ~10,000–12,000 input tokens (including images) + ~500 output tokens
- Estimated cost: **$0.00** (using Google AI Studio Free Tier).

*Commercial pricing assumption: $0.075/1M input tokens, $0.30/1M output tokens = ~$0.0003 per analysis.*
