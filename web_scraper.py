import requests
import json
import os
import time
import threading
from bs4 import BeautifulSoup
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import random

# API Endpoints
YARGITAY_POST_URL = "https://karararama.yargitay.gov.tr/aramalist"
YARGITAY_GET_URL = "https://karararama.yargitay.gov.tr/getDokuman?id={}"

UYAP_POST_URL = "https://emsal.uyap.gov.tr/aramalist"
UYAP_GET_URL = "https://emsal.uyap.gov.tr/getDokuman?id={}"

# Durumu kontrol etmek için değişkenler
is_running = False
start_time = None
tum_kararlar = []
get_request_count = 0 
session = requests.Session()  
elapsed_time = 0
karar_sayisi = 0
current_page = 0
total_pages = 0

# Kaydedilecek dosya adı
DOSYA_ADI = "tum_kararlar.json"

def update_elapsed_time():
    """Geçen süreyi her saniye artırarak UI'de tüm indirme bilgileriyle birlikte günceller."""
    global elapsed_time, is_running, karar_sayisi, tum_kararlar

    while is_running:
        elapsed_time += 1
        
        status_text.set(
            f"📄 Toplam Karar: {karar_sayisi}\n"
            f"📥 İndirilen: {len(tum_kararlar)}\n"
            f"⏳ Kalan: {karar_sayisi - len(tum_kararlar)}\n"
            f"⏩ Sayfa: {current_page}/{total_pages}\n"
            f"⏱ Geçen Süre: {elapsed_time} saniye"
        )
        
        time.sleep(1)


def temizle_html(html_metin):
    """HTML etiketlerini kaldırarak temiz metin döndürür."""
    soup = BeautifulSoup(html_metin, "html.parser")
    temiz_metin = soup.get_text(separator="\n").strip()
    return temiz_metin


def reset_session():
    """Eski session'ı kapatıp yeni bir tane başlatır."""
    global session, get_request_count  

    print("🔄 Yeni bir session açılıyor... 60 saniye bekleniyor...")
    session.close()
    time.sleep(60)
    
    session = requests.Session()
    get_request_count = 0


def api_post_request(aranan_kelime, page_number, kaynak):
    """POST isteği ile karar listesini çeker, hata olursa None döner."""
    url = YARGITAY_POST_URL if kaynak == "yargitay" else UYAP_POST_URL

    payload = {
        "data": {
            "aranan": aranan_kelime,
            "arananKelime": aranan_kelime,
            "pageSize": 100,
            "pageNumber": page_number
        }
    }

    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0',
        "Referer": "https://karararama.yargitay.gov.tr/",
        "Origin": "https://karararama.yargitay.gov.tr/",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        
        json_response = response.json()

        
        if isinstance(json_response, dict) and "data" in json_response and isinstance(json_response["data"], dict):
            return json_response["data"].get("data", None)
        else:
            print(f"⚠️ API beklenmeyen bir yanıt verdi: {json_response}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"❌ POST isteğinde hata oluştu: {e}")
        return None




def api_get_request(doc_id, kaynak):
    """GET isteği ile kararın detaylarını çeker. Hata olursa boş döner."""
    global get_request_count 

    url = YARGITAY_GET_URL.format(doc_id) if kaynak == "yargitay" else UYAP_GET_URL.format(doc_id)

    headers = {
        'Accept': '*/*',
        'User-Agent': random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Mozilla/5.0 (X11; Linux x86_64)"
        ])
    }

    # time.sleep(random.uniform(1.5, 3.5))

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json().get("data", "")

        if not data:
            print(f"⚠️ API boş veri döndürdü! (ID: {doc_id})")
            return ""

        get_request_count += 1

        
        if get_request_count >= 59:
            reset_session()

        return temizle_html(data)

    except requests.exceptions.RequestException as e:
        print(f"❌ GET isteğinde hata oluştu: {e} (ID: {doc_id})")
        return ""
    
   

def karar_indir():
    """Tüm kararları indirir ve belirlenen cihaz aralığında çalıştırır."""
    global is_running, start_time, tum_kararlar, karar_sayisi, current_page, total_pages

    aranan_kelime = keyword_entry.get()
    karar_sayisi = count_entry.get()
    kaynak = source_var.get()
    total_devices = total_devices_entry.get()
    device_id = device_id_entry.get()

    if not aranan_kelime or not karar_sayisi or not total_devices or not device_id:
        status_label.config(text="Lütfen tüm alanları doldurun!", foreground="red")
        return

    karar_sayisi = int(karar_sayisi)
    total_devices = int(total_devices)
    device_id = int(device_id)

    if device_id < 1 or device_id > total_devices:
        status_label.config(text="Geçersiz cihaz ID! 1 ile toplam cihaz sayısı arasında olmalı.", foreground="red")
        return

    dosya_adi = f"tum_kararlar_cihaz{device_id}.json"
    is_running = True
    start_time = time.time()

    if os.path.exists(dosya_adi):
        with open(dosya_adi, "r", encoding="utf-8") as f:
            tum_kararlar = json.load(f)

    mevcut_karar_sayisi = len(tum_kararlar)
    total_pages = ((karar_sayisi + 99) // 100)


    for current_page in range(device_id, total_pages + 1, total_devices):
        if not is_running:
            break

        karar_listesi = api_post_request(aranan_kelime, current_page, kaynak)
        if karar_listesi is None:
            print(f"🚨 Sayfa {current_page} için API boş yanıt döndürdü, 3 saniye bekleyip tekrar deniyoruz...")
            time.sleep(random.uniform(3, 6))
            continue
        elif not karar_listesi:
            print(f"⚠️ Sayfa {current_page} için hiç karar bulunamadı, bir sonraki sayfaya geçiliyor...")
            continue

        for karar in karar_listesi:
            if not is_running:
                break

            doc_id = karar["id"]
            if any(k["id"] == doc_id for k in tum_kararlar):
                continue

            karar_metni = api_get_request(doc_id, kaynak)

            karar["kararMetni"] = karar_metni
            tum_kararlar.append(karar)

            with open(dosya_adi, "w", encoding="utf-8") as f:
                json.dump(tum_kararlar, f, ensure_ascii=False, indent=4)

           
            status_text.set(
                f"📄 Toplam Karar: {karar_sayisi}\n"
                f"📥 İndirilen: {len(tum_kararlar)}\n"
                f"⏳ Kalan: {max(0, karar_sayisi - len(tum_kararlar))}\n"
                f"⏩ Sayfa: {current_page}/{total_pages}\n"
                f"🎯 Cihaz: {device_id}/{total_devices}\n"
                f"⏱ Geçen Süre: {elapsed_time} saniye"
            )
            
            remaining_decisions = karar_sayisi - len(tum_kararlar)

            if remaining_decisions <= 0:
                status_label.config(text="İşlem tamamlandı!", foreground="green")
                is_running = False
                tum_kararlar = []
                keyword_entry.delete(0, 'end')
                count_entry.delete(0, 'end')
                source_var.set("yargitay")
                return

    status_label.config(text="İşlem tamamlandı!", foreground="green")
    is_running = False
    tum_kararlar = []
    keyword_entry.delete(0, 'end')
    count_entry.delete(0, 'end')
    source_var.set("yargitay")


def baslat():
    elapsed_time = 0
    
    threading.Thread(target=update_elapsed_time, daemon=True).start()
    threading.Thread(target=karar_indir, daemon=True).start()
    status_label.config(text="İndirme başlatıldı...", foreground="blue")

def duraklat():
    """Duraklatınca tüm ayarları sıfırlayıp, yeni bir arama için temizler."""
    global is_running, tum_kararlar
    is_running = False
    elapsed_time = 0
    tum_kararlar = []

    keyword_entry.delete(0, 'end')
    count_entry.delete(0, 'end')
    source_var.set("yargitay")

    status_label.config(text="İndirme duraklatıldı! Ayarlar sıfırlandı.", foreground="orange")

# ---------------------- Tkinter UI ----------------------
root = ttk.Window(themename="darkly")
root.title("Karar Arama & İndirme")
root.geometry("550x500")

frame = ttk.Frame(root, padding=20)
frame.pack(expand=True)

# 🔍 Aranan Kelime
ttk.Label(frame, text="🔍 Aranan Kelime:", font=("Arial", 11)).grid(row=0, column=0, sticky=W, pady=5)
keyword_entry = ttk.Entry(frame, width=45, font=("Arial", 11))
keyword_entry.grid(row=0, column=1, pady=5)

# 📄 Karar Sayısı
ttk.Label(frame, text="📄 Karar Sayısı:", font=("Arial", 11)).grid(row=1, column=0, sticky=W, pady=5)
count_entry = ttk.Entry(frame, width=45, font=("Arial", 11))
count_entry.grid(row=1, column=1, pady=5)

# 🔗 Kaynak Seçimi
ttk.Label(frame, text="🔗 Kaynak:", font=("Arial", 11)).grid(row=2, column=0, sticky=W, pady=5)
source_var = ttk.StringVar(value="yargitay")
source_frame = ttk.Frame(frame)
source_frame.grid(row=2, column=1, sticky=W, pady=5)
ttk.Radiobutton(source_frame, text="📌 Yargıtay", variable=source_var, value="yargitay").pack(side=LEFT, padx=5)
ttk.Radiobutton(source_frame, text="📌 UYAP", variable=source_var, value="uyap").pack(side=LEFT, padx=5)

# 🔢 Toplam Cihaz Sayısı
ttk.Label(frame, text="🔢 Toplam Cihaz Sayısı:", font=("Arial", 11)).grid(row=3, column=0, sticky=W, pady=5)
total_devices_entry = ttk.Entry(frame, width=45, font=("Arial", 11))
total_devices_entry.grid(row=3, column=1, pady=5)

# 🎯 Bu Cihaz Kaçıncı?
ttk.Label(frame, text="🎯 Bu Cihaz Kaçıncı?:", font=("Arial", 11)).grid(row=4, column=0, sticky=W, pady=5)
device_id_entry = ttk.Entry(frame, width=45, font=("Arial", 11))
device_id_entry.grid(row=4, column=1, pady=5)

# ⚙️ Butonlar
button_frame = ttk.Frame(frame)
button_frame.grid(row=5, column=0, columnspan=2, pady=15)

ttk.Button(button_frame, text="✅ Başlat", command=baslat, bootstyle=SUCCESS, width=18).pack(side=LEFT, padx=10)
ttk.Button(button_frame, text="⏸️ Duraklat", command=duraklat, bootstyle=DANGER, width=18).pack(side=LEFT, padx=10)

# 📊 Durum Bilgisi (Çerçeveli)
status_frame = ttk.LabelFrame(frame, text="İndirme Durumu", bootstyle="primary", padding=10)
status_frame.grid(row=6, column=0, columnspan=2, pady=10, sticky=W+E)

status_text = ttk.StringVar()
status_label = ttk.Label(status_frame, textvariable=status_text, font=("Arial", 10), wraplength=450)
status_label.pack()


root.mainloop()