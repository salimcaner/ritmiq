import os
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from services.gemini_service import evaluate_quiz_score
from services.deezer_service import check_deezer_connection, get_artists_by_query, generate_quiz_package

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Sunucu Başlatılıyor (Deezer API) ---")
    is_connected = await check_deezer_connection()
    if is_connected:
        print("✅ Deezer API Bağlantısı Başarılı!")
    else:
        print("❌ Deezer API Bağlantısı Başarısız!")
    yield

app = FastAPI(title="RitmiQ", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/search")
async def search_artist(q: str):
    return await get_artists_by_query(q)

@app.get("/api/quiz")
async def get_quiz(artist_id: str, difficulty: str = "medium", count: int = 10):
    return await generate_quiz_package(artist_id, difficulty, count)

@app.get("/api/evaluate")
async def evaluate_score(artist_name: str, correct_count: int, total_count: int):
    message = await evaluate_quiz_score(correct_count, total_count, artist_name)
    return {"message": message}

from fastapi.responses import RedirectResponse, FileResponse

@app.get("/")
async def root():
    return FileResponse("landing.html")

@app.get("/game")
async def game():
    return FileResponse("game.html")

# Frontend dosyalarını sun (JS, CSS, vs.)
app.mount("/", StaticFiles(directory="."), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
