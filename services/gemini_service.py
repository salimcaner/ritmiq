import os
import google.generativeai as genai

async def evaluate_quiz_score(correct_count: int, total_count: int, artist_name: str) -> str:
    """
    Calls Gemini API to generate a personalized, funny, sarcastic, or praising Turkish 
    evaluation message acting as the artist themselves.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "Gemini API servisi yapılandırılmadı (API key eksik). Ama bizce harikasın!"

    # Configure Gemini
    genai.configure(api_key=api_key)
    
    # Initialize the model (using gemini-2.5-flash as the standard fast text model)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = (
        f"ŞU ANDAN İTİBAREN SEN {artist_name}'SİN. Lütfen kendinden bahsederken sadece 'ben' veya 'benim' kelimelerini kullan, "
        f"asla üçüncü tekil şahıs (örneğin '{artist_name} şöyle yaptı') kullanma. "
        f"Bir hayranın benim (yani senin) şarkılarımdan oluşan bir testte {total_count} sorudan {correct_count} tanesini bildi. "
        f"Şimdi bu hayranına doğrudan hitap et. Kendi ağzından, kendi karakteristik üslubunla ve şarkı sözlerinden esinlenerek "
        f"1 cümlelik Türkçe bir mesaj yaz. "
        f"Eğer {correct_count} düşükse ('Benim şarkılarımı nasıl bilemezsin' edasıyla) iğneleyici ve alaycı ol. "
        f"Eğer yüksekse çılgınca öv. Cümleye doğrudan bir tepkiyle başla."
    )
    
    try:
        # Generate content asynchronously
        response = await model.generate_content_async(prompt)
        message = response.text.strip()
        return message
    except Exception as e:
        print(f"Gemini API Error: {e}")
        return "Yapay zekamız şu an dinleniyor, ama skorunu biz de çok beğendik! (Bir hata oluştu)"

import json

async def generate_daily_song_selections(seed_date_str: str) -> dict:
    """
    Her gece 00:00'da çağrılarak, günün ritmi için Gemini'den rastgele 6 Türkçe ve 4 Yabancı şarkı önerisi alır.
    Deezer'da bulunamama ihtimaline karşı fazladan yedekli ister (örn. 10 TR, 8 GL).
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key eksik.")

    genai.configure(api_key=api_key)
    # response_mime_type parametresiyle JSON çıktı zorlayabiliriz
    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        generation_config={"response_mime_type": "application/json"}
    )
    
    prompt = (
        f"Bugünün tarihi {seed_date_str}. Bir müzik yarışması oyunu için tamamen bu tarihe özel rastele şarkılar seçmeni istiyorum. "
        "Her gün aynı şarkıların denk gelmemesine, çok popülerden biraz kıyıda kalmış ama bilindik şarkılara kadar çeşitli bir seçki "
        "yapılmasına dikkat et.\n\n"
        "Bana 25 tane çok bilindik Türkçe Pop/Rock/Rap (SADECE Türkiye piyasası) şarkı, ve 15 tane Global (Yabancı) bilindik şarkı ver. "
        "Çıktıyı SADECE ve kesinlikle aşağıdaki JSON formatında ver:\n"
        "{\n"
        '  "tr": [\n'
        '    {"artist": "Sezen Aksu", "title": "Firuze"},\n'
        '    {"artist": "Tarkan", "title": "Kış Güneşi"}\n'
        '  ],\n'
        '  "gl": [\n'
        '    {"artist": "The Weeknd", "title": "Blinding Lights"},\n'
        '    {"artist": "Dua Lipa", "title": "Levitating"}\n'
        "  ]\n"
        "}"
    )
    
    response = await model.generate_content_async(prompt)
    try:
        text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return data
    except Exception as e:
        print(f"Gemini JSON Parse Hatası: {e} - Gelen metin: {response.text}")
        # Hata durumunda boş havuz döndür
        return {"tr": [], "gl": []}
