# Room Change Detector

A browser-based tool that analyzes before-and-after photographs of a room or desk area and produces a structured change report with paired image-region evidence. No manual labelling required.

## Features

- **Drag-and-drop upload** for before/after photo sets (up to 3 images each)
- **Two-pass GPT-4o analysis**: scene assessment → object-level change detection
- **Evidence crops**: side-by-side before/after image regions for each detected change
- **False positive prevention**: lighting/exposure changes are not reported as physical changes
- **Not-verifiable handling**: objects hidden or out of frame are flagged as "not verifiable" (not "removed")
- **Uncertain matches**: shown separately with suggestions for useful extra angles
- **Cost tracking**: tokens used and estimated cost per analysis

## Quick Start

### Prerequisites
- Python 3.11+
- An OpenAI API key with GPT-4o access

### Setup

```bash
# Clone the repository
cd room-change-detector

# Install dependencies
cd backend
pip install -r requirements.txt

# Generate test images (optional)
cd ../test_sets
python generate_test_set.py

# Start the server
cd ../backend
python app.py
```

### Usage

1. Open `http://localhost:8000` in your browser
2. Enter your OpenAI API key
3. Upload 1-3 "Before" photos and 1-3 "After" photos
4. Click "Analyze Changes"
5. Review the change report with evidence crops

## Project Structure

```
├── backend/
│   ├── app.py              # FastAPI server
│   ├── analyzer.py          # Two-pass GPT-4o analysis engine
│   ├── models.py            # Pydantic data models
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── index.html           # Single-page app
│   ├── style.css            # Responsive styling
│   └── app.js               # Upload handling & result rendering
├── test_sets/
│   ├── generate_test_set.py # Synthetic test image generator
│   ├── expected_results.json# Ground truth (recorded before testing)
│   ├── run_tests.py         # Automated test runner
│   └── set{1,2,3}_{before,after}/  # Generated test images
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
python run_tests.py --api-key sk-your-key-here
```

## AI Tools & Models

- **GPT-4o** (OpenAI): Vision-based image analysis — two API calls per analysis
- **Pillow**: Image cropping for evidence regions
- **FastAPI**: HTTP server
- All other code is original

## Cost Estimates

Per before/after analysis (1 image each, 800×600):
- ~2 GPT-4o API calls
- ~2,000-4,000 input tokens (including images) + ~500-1,000 output tokens
- Estimated cost: **$0.01–$0.03** per analysis

Pricing assumptions: GPT-4o at $2.50/1M input tokens, $10.00/1M output tokens (as of mid-2025).
