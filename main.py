import openai
import json
import os
import pandas as pd
from dotenv import load_dotenv


load_dotenv()


api_key_ai = os.environ.get("OPENAI_API_KEY")


if not api_key_ai:
    raise ValueError("OPENAI_API_KEY bulunamadı. Lütfen .env dosyasını kontrol edin.")
else:
    print(f"API Anahtarı başarıyla yüklendi. (Son 4 hanesi: ...{api_key_ai[-4:]})")


client = openai.OpenAI(api_key=api_key_ai)


def siniflandir_mesaj(mesaj_metni):
    """
    Adım 2: Mesajın ev ilanı olup olmadığını kontrol eder.
    (n8n'deki 'AI Sınıflandırma' node'u)
    """
    print("--- 1. AI Sınıflandırma Adımı Başlatıldı ---")

    prompt = f"""
    Gelen mesaj aşağıdadır:
    ---
    {mesaj_metni}
    ---
    Bu mesaj bir ev ilanı (satılık/kiralık emlak) içeriyor mu?
    Sadece "EVET" veya "HAYIR" olarak cevap ver.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Hızlı ve ucuz bir model
            messages=[
                {"role": "system", "content": "Sen bir sınıflandırma asistanısın."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=5
        )
        cevap = response.choices[0].message.content.strip().upper()
        print(f"Sınıflandırma Sonucu: {cevap}")
        return cevap
    except Exception as e:
        print(f"Sınıflandırma hatası: {e}")
        return "HATA"


def cikar_veri(mesaj_metni):
    """
    Adım 4: Mesajdan yapılandırılmış JSON verisi çıkarır.
    (n8n'deki 'AI Veri Çıkarımı' node'u)
    """
    print("\n--- 2. AI Veri Çıkarımı Adımı Başlatıldı ---")

    # n8n'deki prompt'un aynısı, ancak Python'a uyarlanmış hali
    # Daha iyi JSON uyumluluğu için "ilanlar" adında bir anahtar istiyoruz
    system_prompt = """
    SENARYO: Sen bir emlak verisi çıkarma asistanısın. 
    GÖREV: Sana verilen mesajdaki TÜM ev ilanlarını analiz et ve KURALLARA göre JSON formatında çıkar.

    KURALLAR:
    1. Mesajda birden fazla ilan varsa, her biri "ilanlar" listesinde ayrı bir JSON objesi olmalıdır.
    2. Mesajda bilgi yoksa, ilgili alan için "null" değeri ata. ASLA bilgi uydurma.
    3. "fiyat" ve "metrekare" gibi sayısal değerleri sadece sayı (integer) olarak yaz. (Örn: "5.000.000 TL" -> 5000000).
    4. "orijinal_mesaj" alanına mesajın tam metnini ekle.

    ÇIKTI FORMATI (Sadece bu formatta bir JSON objesi üret):
    {
      "ilanlar": [
        {
          "ilan_turu": "satılık" | "kiralık" | null,
          "konut_tipi": "daire" | "müstakil" | "villa" | "vb." | null,
          "sehir": "...",
          "ilce": "...",
          "mahalle": "...",
          "oda_sayisi": "2+1" | "3+1" | "vb." | null,
          "metrekare": 120 (sadece sayı),
          "fiyat": 5000000 (sadece sayı),
          "para_birimi": "TRY" | "USD" | "EUR" | null,
          "bina_yasi": 5 (sadece sayı),
          "kat": 3 (sadece sayı),
          "esyalimi": "esyalı" | "boş" | null,
          "aciklama_ozet": "Mesajdan çıkarılan kısa bir özet...",
          "orijinal_mesaj": "Mesajın tam metni..."
        }
      ]
    }
    """

    user_prompt = f"İŞLENECEK MESAJ:\n---\n{mesaj_metni}\n---"

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Veri çıkarımı için daha güçlü bir model
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},  # OpenAI'den JSON formatında ısrar et
            temperature=0
        )

        # JSON string'ini Python sözlüğüne (dict) çevir
        json_string = response.choices[0].message.content
        print("AI Ham Çıktısı (JSON String):")
        print(json_string)

        veri = json.loads(json_string)
        return veri.get("ilanlar", [])  # "ilanlar" listesini döndür

    except Exception as e:
        print(f"Veri çıkarma hatası: {e}")
        return []


# --- ANA PROGRAM AKIŞI ---

# Adım 1: Test Verisi (n8n'deki 'Code' node'u)
ornek_mesaj = "Merhaba, elimde 2 adet ilan var. İlki: İzmit, Alikahya'da 3+1 kiralık daire, 120m2, 15.000 TL. İkincisi: Başiskele'de 5+1 satılık lüks villa, 300m2, 25.000.000 TRY, 3 yaşında, full eşyalı."

print(f"Giriş Mesajı: {ornek_mesaj}\n")

# Adım 2: Sınıflandırma
kategori = siniflandir_mesaj(ornek_mesaj)

# Adım 3: Koşul (n8n'deki 'IF' node'u)
if "EVET" in kategori:

    # Adım 4 & 5: Veri Çıkarımı ve Ayrıştırma
    ilan_listesi = cikar_veri(ornek_mesaj)

    # Adım 6: İşleme (Print ve Excel'e Aktarma)
    if ilan_listesi:
        print(f"\n--- SONUÇ: {len(ilan_listesi)} ADET İLAN AYRIŞTIRILDI ---")

        # Orijinal print döngümüz (kontrol için kalabilir)
        for i, ilan in enumerate(ilan_listesi, 1):
            print(f"\n========== İLAN {i} ==========")
            print(json.dumps(ilan, indent=2, ensure_ascii=False))

        print("\n================================")

        # ===============================================
        # ▼▼▼ YENİ EKLENEN EXCEL'E AKTARMA KISMI ▼▼▼
        # ===============================================

        print("\n--- Excel Dosyasına Aktarılıyor ---")
        try:
            # 1. Python listesini (ilan_listesi) bir pandas DataFrame'e dönüştür.
            # Başlıklar (headers) otomatik olarak sözlük anahtarlarından (keys) alınacaktır.
            df = pd.DataFrame(ilan_listesi)

            # 2. DataFrame'i bir Excel dosyasına yazdır.
            excel_dosya_adi = "cikan_ilanlar.xlsx"

            # index=False: Excel'e (0, 1, 2...) şeklinde anlamsız bir sütun eklememesi için
            df.to_excel(excel_dosya_adi, index=False)

            print(f"\n✅ BAŞARILI! Veri '{excel_dosya_adi}' dosyasına kaydedildi.")
            print("Dosyayı projenizin ana klasöründe bulabilirsiniz.")

        except Exception as e:
            print(f"\n❌ HATA: Excel'e yazma sırasında bir sorun oluştu: {e}")

        # ▲▲▲ YENİ EKLENEN KISIM SONU ▲▲▲
        # ===============================================

    else:
        print("\n--- SONUÇ: İlan 'EVET' olarak sınıflandırıldı ancak veri çıkarılamadı. ---")

else:
    print("\n--- SONUÇ: Mesaj ev ilanı olarak sınıflandırılmadı. İşlem durduruldu. ---")