# biletinial-etkinlik-planlayici

1. biletinial_scraper.py çalıştırılır.
  - örn: python biletinial_scraper.py --category both --city antalya --venue-id 20494 2174 1271 --tiyatro-filmtypeids 490 684 688 689 692 569 --opera-filmtypeids 520
2. etkinlik_planlayici.py çalıştırılır.
  - örn: python etkinlik_planlayici.py --start-date "Nisan 18"
3. çıktı doğrudan etkinlik_planlayici_output.txt'den görülebilir.

#### biletinial_scraper parameteleri:
  - *--category both, tiyatro, opera-bale*   (enum, etkinlik turunu belirtir, both tiyatro ve opera-bale çalıştırır)
  - *--city antalya*                          (string, ilgili şehirde arama yapar, zorunlu)
  - *--venue-id 20494*                        (int[], mekan id'leri -biletinial'dan elle kontrol gerekli-)
  - *--tiyatro-filmtypeids 490 684*           (int[], tiyatro kategori id'leri -biletinial'dan elle kontrol gerekli-)
  - *--opera-filmtypeids 490 684*             (int[], opera kategori id'leri -biletinial'dan elle kontrol gerekli-)
  
  
#### etkinlik_planlayici parametreleri:
  - *--start-date Nisan 18*                   (string, plana dahil edilecek ilk gün -boş verilirse filtre uygulanmaz-)
  - *--min-days 4*                            (int, default 4, etkinlikler arası minimum günü belirtir)
  - *--input biletinial_scraper_output.txt*   (str, default "biletinial_scraper_output.txt", girdi dosyasının adı)
  - *--output etkinlik_planlayici_output.txt* (str, default "etkinlik_planlayici_output.txt", çıktı dosyasının adı.)
