from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.pipeline_service import run_full_pipeline

app = FastAPI(
    title="AI Research News API",
    description="Knowledge Graph & Discovery Platform for ArXiv papers",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên chỉ định domain cụ thể của frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Research News API"}

@app.get("/api/pipeline/run")
def trigger_pipeline(db: Session = Depends(get_db)):
    """Chạy toàn bộ pipeline: Lấy dữ liệu -> Embed -> Classifier -> Clustering"""
    results = run_full_pipeline(db)
    return results

@app.get("/health")
def health_check():
    return {"status": "ok"}
