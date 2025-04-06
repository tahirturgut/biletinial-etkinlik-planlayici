import re
import argparse
from datetime import datetime, timedelta

# python etkinlik_planlayici.py --start-date "Nisan 18" ; "(Roo/PS Workaround: 34)" > $null; start-sleep -milliseconds 150

# Türkçe ay isimleri ve tarih işlemleri için locale ayarı kaldırıldı.
# Doğrudan ay çeviri sözlüğü kullanılacak.

# Türkçe ay isimlerini İngilizce'ye çevirmek için sözlük
ay_ceviri = {
    "Ocak": "January", "Şubat": "February", "Mart": "March", "Nisan": "April",
    "Mayıs": "May", "Haziran": "June", "Temmuz": "July", "Ağustos": "August",
    "Eylül": "September", "Ekim": "October", "Kasım": "November", "Aralık": "December"
}
# İngilizce ay isimlerini Türkçe'ye çevirmek için ters sözlük
ay_ceviri_ters = {v: k for k, v in ay_ceviri.items()}

# Yılı dinamik olarak alalım
current_year = datetime.now().year

def parse_start_date(date_str, year, ay_ceviri_dict):
    """Verilen 'Ay Gün' formatındaki stringi datetime nesnesine çevirir."""
    try:
        parts = date_str.split()
        if len(parts) != 2:
            raise ValueError("Tarih formatı 'Ay Gün' olmalı (örn: Mayıs 11)")
        month_tr, day_str = parts
        month_en = ay_ceviri_dict.get(month_tr.capitalize())
        if not month_en:
            raise ValueError(f"Geçersiz ay adı: {month_tr}")
        day = int(day_str)
        start_date_obj = datetime.strptime(f"{day} {month_en} {year}", "%d %B %Y")
        # Saat/dakika/saniye bilgisini sıfırlayarak sadece gün bazında karşılaştırma yapalım
        return start_date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
    except ValueError as e:
        print(f"Başlangıç tarihi ayrıştırma hatası: {e}")
        return None
    except Exception as e:
        print(f"Beklenmedik başlangıç tarihi hatası: {e}")
        return None

def parse_events(text, year, ay_ceviri_dict):
    """Metinden etkinlikleri ayrıştırır ve tarih bilgisi ekler."""
    events = []
    current_month_str = None
    current_day = None

    # Etkinlik satırını yakalamak için regex
    event_pattern = re.compile(r"^\s*-\s*(\[.*?\])\s*(.*?)\s*->\s*(https?://.*)")

    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or "---" in line:
            continue

        # Tarih satırı kontrolü (örn: Nisan - 10:)
        date_match = re.match(r"(\w+)\s*-\s*(\d+):", line)
        if date_match:
            current_month_str = date_match.group(1).capitalize()
            current_day = int(date_match.group(2))
            continue

        # Etkinlik satırı kontrolü
        event_match = event_pattern.match(line)
        if event_match and current_month_str and current_day:
            event_type = event_match.group(1)
            details = event_match.group(2).strip()
            url = event_match.group(3).strip()

            # Etkinlik ismini ayıklama (Genellikle '–' öncesi kısım)
            event_name = details.split('–')[0].strip()

            # Tarih oluşturma (locale bağımsız)
            month_en = ay_ceviri_dict.get(current_month_str)
            if not month_en:
                print(f"Bilinmeyen ay: {current_month_str}")
                continue

            try:
                date_str_en = f"{current_day} {month_en} {year}"
                # İngilizce ay ismine göre parse et (%B formatı İngilizce ay isimlerini bekler)
                event_date = datetime.strptime(date_str_en, "%d %B %Y")
                # Tarih karşılaştırması için saat/dakika/saniye sıfırlama
                event_date = event_date.replace(hour=0, minute=0, second=0, microsecond=0)
            except ValueError:
                print(f"Tarih dönüştürme hatası: {date_str_en}")
                continue
            except Exception as e:
                 print(f"Beklenmedik tarih hatası: {e}, Tarih: {date_str_en}")
                 continue

            events.append({
                'date': event_date,
                'name': event_name,
                'full_detail': line.lstrip('- ') # Orijinal formatı koru
            })

    # Etkinlikleri tarihe göre sırala
    events.sort(key=lambda x: x['date'])
    return events

def create_plan(events, min_days_apart=3):
    """Verilen etkinlik listesinden, aynı isimli oyunları tekrarlamadan ve belirli gün aralığıyla plan oluşturur."""
    planned_events = []
    planned_names = set()
    last_event_date = None

    for event in events:
        event_name = event['name']
        event_date = event['date']

        # Eğer bu oyun daha önce plana eklenmediyse
        if event_name not in planned_names:
            # Eğer ilk etkinlikse veya son etkinlikten yeterince gün geçtiyse
            if last_event_date is None or (event_date - last_event_date).days >= min_days_apart:
                planned_events.append(event)
                planned_names.add(event_name)
                last_event_date = event_date

    return planned_events

def format_plan(planned_events):
    """Oluşturulan planı okunabilir formatta string'e çevirir."""
    if not planned_events:
        return "--- Önerilen Plan ---\n(Belirtilen kriterlere uygun etkinlik bulunamadı)\n------------------------------"

    output = ["--- Önerilen Plan ---"]
    grouped_by_date = {}

    for event in planned_events:
        # Gruplama ve sıralama için İngilizce ay ismiyle tarih anahtarı oluştur
        date_str = event['date'].strftime("%B - %d")
        if date_str not in grouped_by_date:
            grouped_by_date[date_str] = []
        grouped_by_date[date_str].append(event['full_detail'])

    # Tarihe göre sıralı yazdırma
    # Sözlüğü tarihe göre sıralamak için datetime nesnelerine geri dönelim
    # Yıl bilgisi önemli değil, sadece ay ve gün sıralaması için kullanılıyor
    sorted_dates = sorted(grouped_by_date.keys(), key=lambda d: datetime.strptime(f"{d.split(' - ')[1]} {d.split(' - ')[0]} 2000", f"%d %B %Y"))


    for date_key in sorted_dates: # date_key örn: "April - 10"
        month_en, day_str = date_key.split(' - ')
        month_tr = ay_ceviri_ters.get(month_en, month_en) # İngilizce ayı Türkçe'ye çevir
        output.append(f"\n{month_tr} - {day_str}:") # Türkçe ay ismiyle yazdır
        for detail in grouped_by_date[date_key]:
            output.append(f"  - {detail}")

    output.append("\n------------------------------")
    return "\n".join(output)

# Ana işlem akışı
if __name__ == "__main__":
    # Argümanları işle
    parser = argparse.ArgumentParser(description="Biletinial etkinliklerinden plan oluşturur.")
    parser.add_argument("--start-date", type=str, help="Planın başlayacağı tarih (örn: 'Mayıs 11'). Bu tarihten önceki etkinlikler dahil edilmez.")
    parser.add_argument("--input", type=str, default="biletinial_scraper_output.txt", help="Girdi dosyasının adı.")
    parser.add_argument("--output", type=str, default="etkinlik_planlayici_output.txt", help="Çıktı dosyasının adı.")
    parser.add_argument("--min-days", type=int, default=4, help="Aynı isimli oyunlar arasındaki minimum gün sayısı.")
    args = parser.parse_args()

    start_date = None
    if args.start_date:
        start_date = parse_start_date(args.start_date, current_year, ay_ceviri)
        if start_date:
            print(f"Plan başlangıç tarihi olarak ayarlandı: {start_date.strftime('%d %B %Y (%A)')}")
        else:
            print("Geçersiz başlangıç tarihi formatı nedeniyle tarih filtresi uygulanmayacak.")
            # İsteğe bağlı: Hatalı tarih durumunda çıkış yapılabilir
            # import sys
            # sys.exit(1)

    # Girdi ve çıktı dosyaları
    input_filename = args.input
    output_filename = args.output

    # Girdi dosyasını oku
    request_text = ""
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            request_text = f.read()
        print(f"'{input_filename}' dosyasından etkinlikler okundu.")
    except FileNotFoundError:
        print(f"Hata: Girdi dosyası '{input_filename}' bulunamadı.")
    except Exception as e:
        print(f"Hata: Girdi dosyası okunurken bir sorun oluştu: {e}")

    if request_text: # Sadece girdi varsa devam et
        all_events = parse_events(request_text, current_year, ay_ceviri)

        # Başlangıç tarihine göre filtrele
        if start_date:
            original_count = len(all_events)
            filtered_events = [event for event in all_events if event['date'] >= start_date]
            filtered_count = len(filtered_events)
            print(f"{original_count - filtered_count} etkinlik başlangıç tarihinden ({start_date.strftime('%d %b')}) önce olduğu için filtrelendi.")
        else:
            filtered_events = all_events # Filtreleme yok
            print("Başlangıç tarihi belirtilmediği için tüm etkinlikler dikkate alınıyor.")

        if not filtered_events:
             print("Belirtilen başlangıç tarihinden sonra veya genel olarak işlenecek etkinlik bulunamadı.")
             formatted_output = format_plan([]) # Boş plan formatla
        else:
            suggested_plan = create_plan(filtered_events, min_days_apart=args.min_days)
            formatted_output = format_plan(suggested_plan)

        # Çıktıyı dosyaya yaz
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(formatted_output)
            print(f"Plan başarıyla '{output_filename}' dosyasına yazıldı.")
        except Exception as e:
            print(f"Hata: Çıktı dosyasına yazılırken bir sorun oluştu: {e}")
            print("\n--- Plan (Dosyaya Yazılamadı) ---")
            print(formatted_output)
            print("---------------------------------")
    else:
        print("Girdi metni boş veya okunamadı. Plan oluşturulamadı.")