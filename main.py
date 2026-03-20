import os
import random
import datetime
import asyncio
import traceback
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from redis.asyncio import Redis
from services.gemini_service import evaluate_quiz_score, generate_daily_song_selections
from services.deezer_service import check_deezer_connection, get_artists_by_query, generate_quiz_package

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
DAILY_CACHE_TTL_SECONDS = 48 * 60 * 60  # 48 saat
DAILY_LOCK_TTL_SECONDS = 15 * 60  # 15 dakika
REDIS_CLIENT = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global REDIS_CLIENT
    print("--- Sunucu Başlatılıyor (Deezer API) ---")
    is_connected = await check_deezer_connection()
    if is_connected:
        print("✅ Deezer API Bağlantısı Başarılı!")
    else:
        print("❌ Deezer API Bağlantısı Başarısız!")

    if REDIS_URL:
        try:
            REDIS_CLIENT = Redis.from_url(REDIS_URL, decode_responses=True)
            await REDIS_CLIENT.ping()
            print("✅ Redis bağlantısı başarılı!")
        except Exception as e:
            print(f"❌ Redis bağlantısı başarısız: {e}")
            REDIS_CLIENT = None
    else:
        print("⚠️ REDIS_URL tanımlı değil. Geçici bellek önbelleği kullanılacak.")
        
    loop_task = asyncio.create_task(daily_quiz_generator_loop())
    yield
    loop_task.cancel()
    if REDIS_CLIENT:
        await REDIS_CLIENT.aclose()

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

# --- GÜNÜN RİTMİ ÖNBELLEĞİ (Sıfır Sapma - Tüm Kullanıcılara Birebir Aynı Liste) ---
DAILY_QUIZ_CACHE = {
    "date": None,
    "quiz_data": None
}


def _daily_quiz_key(date_str: str) -> str:
    return f"daily_quiz:{date_str}"


def _daily_lock_key(date_str: str) -> str:
    return f"daily_quiz_lock:{date_str}"


def _is_old_cache_format(quiz_data: dict) -> bool:
    """Eski format: audio_url var, track_id yok (süresi dolan URL'ler)."""
    questions = quiz_data.get("questions", []) or []
    if not questions:
        return False
    q = questions[0]
    return bool(q.get("audio_url")) and not q.get("track_id")


async def _clear_daily_cache(date_str: str):
    """Bugünün cache'ini siler (yeniden üretim için)."""
    if REDIS_CLIENT:
        await REDIS_CLIENT.delete(_daily_quiz_key(date_str))
    if DAILY_QUIZ_CACHE["date"] == date_str:
        DAILY_QUIZ_CACHE["date"] = None
        DAILY_QUIZ_CACHE["quiz_data"] = None


async def _get_daily_quiz(date_str: str):
    if REDIS_CLIENT:
        raw_data = await REDIS_CLIENT.get(_daily_quiz_key(date_str))
        if raw_data:
            data = json.loads(raw_data)
            if _is_old_cache_format(data):
                await _clear_daily_cache(date_str)
                return None
            return data
        return None

    if DAILY_QUIZ_CACHE["date"] == date_str:
        data = DAILY_QUIZ_CACHE["quiz_data"]
        if data and _is_old_cache_format(data):
            await _clear_daily_cache(date_str)
            return None
        return data
    return None


async def _set_daily_quiz(date_str: str, quiz_data: dict):
    if REDIS_CLIENT:
        await REDIS_CLIENT.set(
            _daily_quiz_key(date_str),
            json.dumps(quiz_data, ensure_ascii=False),
            ex=DAILY_CACHE_TTL_SECONDS
        )
        return

    DAILY_QUIZ_CACHE["date"] = date_str
    DAILY_QUIZ_CACHE["quiz_data"] = quiz_data


async def _acquire_generation_lock(date_str: str) -> bool:
    if not REDIS_CLIENT:
        return True
    return bool(await REDIS_CLIENT.set(_daily_lock_key(date_str), "1", ex=DAILY_LOCK_TTL_SECONDS, nx=True))


async def _release_generation_lock(date_str: str):
    if REDIS_CLIENT:
        await REDIS_CLIENT.delete(_daily_lock_key(date_str))


async def _run_regenerate_then_clear(today_str: str):
    """Arka planda günlük quiz üretir, bittiğinde flag temizlenir."""
    try:
        await generate_and_cache_daily_quiz(today_str)
    except Exception as e:
        print(f"Arka plan günlük quiz hatası: {e}")
        traceback.print_exc()
    finally:
        _regn_done.discard(today_str)


async def _enrich_daily_quiz_with_previews(quiz_data: dict) -> dict:
    """Her soru için Deezer'dan güncel preview URL alır, audio_url ekler."""
    questions = quiz_data.get("questions", [])
    if not questions:
        return quiz_data

    track_ids = [q["track_id"] for q in questions if q.get("track_id")]
    if not track_ids:
        return quiz_data

    async def fetch_preview(client: httpx.AsyncClient, track_id: int) -> str | None:
        try:
            resp = await client.get(f"https://api.deezer.com/track/{track_id}")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("preview")
        except Exception:
            pass
        return None

    async with httpx.AsyncClient(timeout=10.0) as client:
        previews = await asyncio.gather(*[fetch_preview(client, tid) for tid in track_ids])

    enriched = []
    idx = 0
    for q in questions:
        if q.get("audio_url"):
            enriched.append(q)
            continue
        if q.get("track_id") and idx < len(previews):
            url = previews[idx]
            idx += 1
            if url:
                q = {**q, "audio_url": url}
                enriched.append(q)
            # preview yoksa soruyu atla
    return {
        **quiz_data,
        "questions": enriched,
        "total": len(enriched),
    }


async def generate_and_cache_daily_quiz(today_str: str):
    print(f"--- {today_str} İÇİN GÜNÜN RİTMİ OLUŞTURULUYOR (Gemini API) ---")
    
    gemini_data = await generate_daily_song_selections(today_str)
    tr_list = gemini_data.get("tr", [])
    gl_list = gemini_data.get("gl", [])
    
    tr_tracks_with_preview = []
    gl_tracks_with_preview = []
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        sem = asyncio.Semaphore(5)
        
        async def search_track(item):
            artist = item.get("artist", "")
            title = item.get("title", "")
            if not artist or not title: return None
            
            async with sem:
                try:
                    s_resp = await client.get(f"https://api.deezer.com/search", params={"q": f'artist:"{artist}" track:"{title}"', "limit": 1})
                    s_data = s_resp.json().get("data", [])
                    if not s_data:
                        s_resp = await client.get(f"https://api.deezer.com/search", params={"q": f"{artist} {title}", "limit": 1})
                        s_data = s_resp.json().get("data", [])
                    if s_data and s_data[0].get("preview"):
                        return s_data[0]
                except:
                    pass
            return None

        print(f"Gemini'nin önerdiği şarkılar Deezer'da aranıyor... ({len(tr_list)} TR, {len(gl_list)} GL)")
        tasks_tr = [search_track(t) for t in tr_list]
        tasks_gl = [search_track(t) for t in gl_list]
        
        tr_results = await asyncio.gather(*tasks_tr)
        gl_results = await asyncio.gather(*tasks_gl)
        
        for t in tr_results:
            if t and t["id"] not in [x["id"] for x in tr_tracks_with_preview]: 
                tr_tracks_with_preview.append(t)
        for t in gl_results:
            if t and t["id"] not in [x["id"] for x in gl_tracks_with_preview]: 
                gl_tracks_with_preview.append(t)
                
        print(f"Eşleşen TR: {len(tr_tracks_with_preview)} | Eşleşen GL: {len(gl_tracks_with_preview)}")
        
        tr_correct_tracks = tr_tracks_with_preview[:6]
        gl_correct_tracks = gl_tracks_with_preview[:4]
        
        questions = []
        
        import random
        for correct_track in tr_correct_tracks:
            # Artık Deezer playlisti yerine doğrudan Gemini'nin verdiği zengin isim havuzunu kullanıyoruz!
            pool = [t for t in tr_list if t.get("title") and t.get("title").lower() != correct_track["title"].lower()]
            distractors = random.sample(pool, min(len(pool), 3))
            
            options = [correct_track["title"]] + [t["title"] for t in distractors]
            random.shuffle(options)
            
            album = correct_track.get("album", {})
            questions.append({
                "track_id": correct_track["id"],
                "options": options,
                "correct_answer": correct_track["title"],
                "track_info": {
                    "name": correct_track["title"],
                    "artist": correct_track.get("artist", {}).get("name", "Bilinmeyen"),
                    "album": album.get("title", ""),
                    "image": album.get("cover_medium", "")
                }
            })

        for correct_track in gl_correct_tracks:
            pool = [t for t in gl_list if t.get("title") and t.get("title").lower() != correct_track["title"].lower()]
            distractors = random.sample(pool, min(len(pool), 3))
            
            options = [correct_track["title"]] + [t["title"] for t in distractors]
            random.shuffle(options)
            
            album = correct_track.get("album", {})
            questions.append({
                "track_id": correct_track["id"],
                "options": options,
                "correct_answer": correct_track["title"],
                "track_info": {
                    "name": correct_track["title"],
                    "artist": correct_track.get("artist", {}).get("name", "Bilinmeyen"),
                    "album": album.get("title", ""),
                    "image": album.get("cover_medium", "")
                }
            })

        random.shuffle(questions)
        
        daily_quiz_payload = {
            "mode": "daily",
            "date": today_str,
            "total": len(questions),
            "questions": questions
        }
        await _set_daily_quiz(today_str, daily_quiz_payload)
        print("✅ GÜNÜN RİTMİ HAZIRLANDI VE ÖNBELLEĞE ALINDI!")


async def daily_quiz_generator_loop():
    while True:
        try:
            today_str = datetime.date.today().strftime("%Y%m%d")
            cached_today = await _get_daily_quiz(today_str)

            if not cached_today:
                lock_acquired = await _acquire_generation_lock(today_str)
                if lock_acquired:
                    try:
                        await generate_and_cache_daily_quiz(today_str)
                    finally:
                        await _release_generation_lock(today_str)
                else:
                    print("Günün ritmi başka bir worker tarafından hazırlanıyor...")
                
        except Exception as e:
            print(f"Daily quiz generator loop error: {e}")
            traceback.print_exc()

        now = datetime.datetime.now()
        tomorrow = now.date() + datetime.timedelta(days=1)
        next_midnight = datetime.datetime.combine(tomorrow, datetime.time.min)
        
        seconds_to_wait = (next_midnight - now).total_seconds()
        seconds_to_wait += 5 # 00:00:05'te çalışması için tolerans
        
        print(f"Günün ritmi belirlendi. Saat 00:00'a kadar yaklaşık {int(seconds_to_wait // 3600)} saat bekleniyor...")
        await asyncio.sleep(seconds_to_wait)


_regn_lock = asyncio.Lock()
_regn_done = set()


@app.get("/api/daily")
async def get_daily_quiz():
    today_str = datetime.date.today().strftime("%Y%m%d")
    quiz_data = await _get_daily_quiz(today_str)
    if quiz_data:
        quiz_data = await _enrich_daily_quiz_with_previews(quiz_data)
        if quiz_data.get("questions"):
            return quiz_data
    # Cache boş veya eski format silindi: arka planda yeniden üret
    async with _regn_lock:
        if today_str not in _regn_done:
            _regn_done.add(today_str)
            asyncio.create_task(_run_regenerate_then_clear(today_str))
    raise HTTPException(status_code=503, detail="Günün Ritmi güncelleniyor, lütfen 1-2 dakika sonra tekrar deneyin.")

from fastapi.responses import RedirectResponse, FileResponse

@app.get("/")
async def root():
    return FileResponse("templates/landing.html")

@app.get("/game")
@app.get("/game.html")
async def game():
    return FileResponse("templates/game.html")

@app.get("/terms")
@app.get("/terms.html")
async def terms():
    return FileResponse("templates/terms.html")

@app.get("/privacy")
@app.get("/privacy.html")
async def privacy():
    return FileResponse("templates/privacy.html")

@app.get("/index.html")
async def index():
    return FileResponse("templates/index.html")

# Frontend dosyalarını sun (JS, CSS, vs.)
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
