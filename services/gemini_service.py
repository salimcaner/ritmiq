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
