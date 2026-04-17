# Kod mantığı — RitmiQ

Backend ve tek sayfa oyunu birlikte okumak için pratik sıra.

## 1. Giriş noktası: `main.py`

- **`lifespan`**: Uygulama açılırken Deezer erişimini test eder; `REDIS_URL` varsa Redis’e bağlanır; `daily_quiz_generator_loop` arka plan görevini başlatır.
- **Route’lar**:
  - `GET /api/search?q=` → `get_artists_by_query` (Deezer).
  - `GET /api/quiz?artist_id=&difficulty=&count=` → `generate_quiz_package` (Deezer).
  - `GET /api/evaluate?...` → `evaluate_quiz_score` (Gemini; anahtar yoksa sabit mesaj).
  - `GET /api/daily` → Bugünün tarihine göre önbellekten günlük quiz; boş/eskimişse arka planda yeniden üretim tetiklenebilir, hazır değilse 503.
- **Sayfalar**: `FileResponse` ile `templates/` altındaki HTML dosyaları.
- **`app.mount("/static", ...)`**: `static/css`, `static/js` tarayıcıda `/static/...` yolundan servis edilir.

Önbellek yardımcıları: `_get_daily_quiz`, `_set_daily_quiz`, `_enrich_daily_quiz_with_previews` (Deezer’dan güncel `preview` URL).

## 2. Deezer: `services/deezer_service.py`

- **`check_deezer_connection`**: Basit HTTP ile API ayakta mı kontrolü.
- **`get_artists_by_query`**: Arama sonucundan ilk birkaç sanatçıyı frontend’in beklediği forma çevirir.
- **`generate_quiz_package`**: Sanatçının top şarkılarını çeker, preview’lı olanlardan havuz oluşturur, zorluğa göre havuz boyutu kısar; her soru için doğru şarkı + 3 distractor şarkı adı, `audio_url` = preview.

## 3. Gemini: `services/gemini_service.py`

- **`evaluate_quiz_score`**: Sanatçı rolünde kısa Türkçe mesaj (model: `gemini-2.5-flash`).
- **`generate_daily_song_selections`**: Tarih tohumlu prompt ile TR ve global şarkı listesi JSON döner; `GEMINI_API_KEY` zorunlu.

## 4. İstemci: `static/js/script.js`

- **Durum**: `selectedArtist`, `questions`, `isDailyMode`, zorluk seçimleri vb.
- **Klasik oyun**: `startGame` → `GET /api/quiz?artist_id=...` → `loadQuestion` ile `audio_url` oynatma, şıklar, süre/progress.
- **Günün ritmi**: `startDailyGame` → `GET /api/daily`; bugün için `localStorage` varsa API’yi atlayıp sonuç ekranına gidebilir.
- **Sonuç**: Klasik modda “Sanatçı notu” `GET /api/evaluate` ile Gemini mesajı alır (`selectedArtist.name` gerekir). Günün ritmi modunda bu buton gizlenir; günlük skor `localStorage` ile tutulur.

## 5. Okuma sırası önerisi

1. `main.py` — route listesi ve `/api/daily` + önbellek fonksiyonları.
2. `deezer_service.py` — klasik quiz nasıl üretiliyor.
3. `gemini_service.py` — günlük liste ve değerlendirme.
4. `static/js/script.js` — `startGame`, `startDailyGame`, `loadQuestion`, sonuç akışı.

Bu yeterli bağlamla hem HTTP sözleşmesini hem veri şekillerini (`questions` içinde `audio_url`, `options`, `correct_answer`, günlük modda `track_id`) takip edebilirsin.
