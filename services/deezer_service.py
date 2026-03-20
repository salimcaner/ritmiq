import random
import httpx
from fastapi import HTTPException

DEEZER_BASE = "https://api.deezer.com"

async def check_deezer_connection():
    """Bağlantıyı test eder, başarılı olup olmadığını döndürür."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{DEEZER_BASE}/search/artist?q=test", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

async def get_artists_by_query(query: str):
    """Verilen sorguya göre Deezer API'den sanatçı listesini döndürür."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{DEEZER_BASE}/search/artist", params={"q": query, "order": "RANKING"})
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

async def generate_quiz_package(artist_id: str, difficulty: str = "medium", count: int = 10):
    """Verilen sanatçı için belirtilen zorlukta quiz paketi oluşturur."""
    diff_limits = {
        "easy": 10,
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

        # Şarkıları çek
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

        pool = tracks_with_preview[:pool_size] if len(tracks_with_preview) >= pool_size else tracks_with_preview
        actual_count = min(count, len(pool))
        
        if actual_count < 1:
            raise HTTPException(status_code=404, detail="Yeterli şarkı bulunamadı.")

        correct_tracks = random.sample(pool, actual_count)
        questions = []
        
        for correct_track in correct_tracks:
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
