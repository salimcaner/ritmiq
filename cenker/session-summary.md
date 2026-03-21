## Özet

- `.gitignore`: Yerel Cursor ayarları ve skill/komut dosyalarının yanlışlıkla repoya girmemesi için `.cursor/` eklendi.
- `cenker/`: Projeyi çalıştırma notları, mimari diyagram özeti ve kod okuma rehberi (dokümantasyon).

## Neden

Takımın yerel Cursor yapılandırmasını repoda tutmama tercihi; geliştiriciler için merkezi dokümantasyon klasörü.

## Risk / test

- Üretim veya runtime davranışını değiştirmez; yalnızca ignore kuralı ve Markdown dosyaları.
- Test gerekmez.

## Checklist

- [ ] `cenker/` içeriği repoda paylaşılmak istenen metinler mi?
- [ ] `.cursor/` ignore’u tüm ekip için uygun mu (bazı projeler `.cursor/rules` seçici commit eder)?
