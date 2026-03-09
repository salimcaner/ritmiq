import os
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

DEEZER_BASE = "https://api.deezer.com"

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- Sunucu Başlatılıyor (Deezer API) ---")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DEEZER_BASE}/search/artist?q=test")
        if resp.status_code == 200:
            print("✅ Deezer API Bağlantısı Başarılı!")
        else:
            print(f"❌ Deezer API Bağlantısı Başarısız: {resp.status_code}")
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
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DEEZER_BASE}/search/artist", params={"q": q})
        if resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Deezer API hatası")
        data = resp.json()
        artists = data.get("data", [])
        return {
            "artists": {
                "items": [
                    {
                        "id": str(a["id"]),
                        "name": a["name"],
                        "images": [{"url": a.get("picture_medium", "")}],
                    }
                    for a in artists[:5]
                ]
            }
        }

@app.get("/api/quiz")
async def get_quiz(artist_id: str, difficulty: str = "medium", count: int = 10):
    """10 soruluk quiz paketi döndürür"""
    diff_limits = {
        "easy": 10,    # İlk 10 (en popüler)
        "medium": 25,
        "hard": 50
    }
    pool_size = diff_limits.get(difficulty, 25)

    async with httpx.AsyncClient(timeout=20.0) as client:
        # Sanatçı bilgisi
        artist_resp = await client.get(f"{DEEZER_BASE}/artist/{artist_id}")
        if artist_resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Sanatçı bulunamadı.")
        artist_name = artist_resp.json().get("name", "Bilinmeyen Sanatçı")

        # Tüm şarkıları çek (max 50)
        tracks_resp = await client.get(
            f"{DEEZER_BASE}/artist/{artist_id}/top",
            params={"limit": 50}
        )
        if tracks_resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Şarkılar alınamadı.")

        all_tracks = tracks_resp.json().get("data", [])
        tracks_with_preview = [t for t in all_tracks if t.get("preview")]

        print(f"DEBUG: {artist_name}: {len(all_tracks)} şarkı, {len(tracks_with_preview)} önizlemeli")

        if len(tracks_with_preview) < 4:
            raise HTTPException(
                status_code=404,
                detail=f"{artist_name} için yeterli şarkı önizlemesi bulunamadı (en az 4 gerekli)."
            )

        # Zorluk havuzunu sınırla, ama en az 4 olsun
        pool = tracks_with_preview[:pool_size] if len(tracks_with_preview) >= pool_size else tracks_with_preview

        # Kaç soru sorulacak: max(count) veya havuz kadar
        actual_count = min(count, len(pool))
        if actual_count < 1:
            raise HTTPException(status_code=404, detail="Yeterli şarkı bulunamadı.")

        # Doğru cevaplar: pool'dan rastgele actual_count tane
        correct_tracks = random.sample(pool, actual_count)

        questions = []
        for correct_track in correct_tracks:
            # Şıklar: doğru + 3 yanlış (tüm şarkılar havuzundan)
            distractors_pool = [t for t in all_tracks if t["id"] != correct_track["id"]]
            distractors = random.sample(distractors_pool, min(len(distractors_pool), 3))

            options = [correct_track["title"]] + [t["title"] for t in distractors]
            random.shuffle(options)

            album = correct_track.get("album", {})
            questions.append({
                "audio_url": correct_track["preview"],
                "options": options,
                "correct_answer": correct_track["title"],
                "track_info": {
                    "name": correct_track["title"],
                    "album": album.get("title", ""),
                    "image": album.get("cover_medium", "")
                }
            })

        return {
            "artist_name": artist_name,
            "total": actual_count,
            "questions": questions
        }

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
