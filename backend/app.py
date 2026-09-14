from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import List
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv

from analyzer import analyze_images, create_evidence_pairs

load_dotenv()  # Load variables from .env file

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

@app.post("/api/analyze")
async def analyze(
    before_images: List[UploadFile] = File(...),
    after_images: List[UploadFile] = File(...)
):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Server misconfiguration: GEMINI_API_KEY not found in .env")

    if len(before_images) > 3 or len(after_images) > 3:
        raise HTTPException(status_code=400, detail="Maximum 3 images allowed per set.")
    
    b_bytes = [await file.read() for file in before_images]
    a_bytes = [await file.read() for file in after_images]
    
    try:
        result = analyze_images(b_bytes, a_bytes, api_key)
        evidence = create_evidence_pairs(b_bytes, a_bytes, result)
        
        response_data = result.model_dump()
        response_data["evidence_crops"] = evidence
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    index_path = os.path.join(frontend_dir, 'index.html')
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Frontend index.html not found."}

if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

test_sets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_sets'))
if os.path.exists(test_sets_dir):
    app.mount("/test_sets", StaticFiles(directory=test_sets_dir), name="test_sets")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
