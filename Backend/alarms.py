import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from exponent_server_sdk import PushClient, PushMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from zoneinfo import ZoneInfo

# Veri üretimi fonksiyonunu import ediyoruz
from data import sagim_verisi_uret_ve_kaydet

load_dotenv()

try:
    from sql_rag import local_llm
except ImportError:
    from langchain_ollama import ChatOllama
    local_llm = ChatOllama(
        model=os.getenv("LOCAL_LLM"),
        temperature=0.1,
        base_url=os.getenv("OLLAMA_BASE_URL")
    )

def get_db_connection():
    db_user = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME")
    
    return psycopg2.connect(
        dbname=db_name,
        user=db_user,
        password=db_password,
        host=db_host,
        port=int(db_port)
    )

def send_push_notification(title: str, body: str, data: dict = None):
    """Kayıtlı tüm cihaz token'larına push bildirimi gönderir."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT token FROM cihaz_tokenlari;")
        tokens = cursor.fetchall()
        cursor.close()
        
        if not tokens:
            print("Bildirim gönderilecek kayıtlı push token bulunamadı.")
            return

        client = PushClient()
        basarili_sayisi = 0
        
        for (token,) in tokens:
            if not (token.startswith("ExponentPushToken") or token.startswith("ExpoPushToken")):
                print(f"⚠️ Geçersiz push token formatı atlanıyor: {token}")
                continue
            
            try:
                notification_data = {"target_screen": "Notifications"}
                if data:
                    notification_data.update(data)

                client.publish(
                    PushMessage(
                        to=token,
                        title=title,
                        body=body,
                        sound="default",
                        priority="high",
                        channel_id="default",
                        data=notification_data
                    )
                )
                basarili_sayisi += 1
            except Exception as e:
                print(f"❌ '{token}' cihazına bildirim gönderilirken hata oluştu: {e}")
                
        if basarili_sayisi > 0:
            print(f"✅ Toplam {basarili_sayisi} cihaza push bildirimi başarıyla gönderildi.")
            
    except Exception as e:
        print(f"❌ Veritabanı veya Push bildirim genel hatası: {e}")
    finally:
        if conn:
            conn.close()

def check_for_milk_drops():
    """
    Tüm ineklerin son sağım kayıtlarını analiz eder. 
    Eğer bir ineğin son sağımı, önceki 3 sağım ortalamasına kıyasla %20 veya daha fazla düşmüşse
    ineğin bağlı olduğu ciftlik_id ile birlikte alarm oluşturur.
    """
    print("Süt düşüş analizi başlatılıyor...")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # YENİ: inekler tablosundan (i.ciftlik_id) çekildi, null ise 1 varsayıldı
        query = """
        WITH son_kayitlar AS (
            SELECT DISTINCT ON (kupe_no)
                id,
                kupe_no,
                tarih,
                sagim_zamani,
                sut_miktari
            FROM sagim_kayitlari
            ORDER BY kupe_no, tarih DESC, id DESC
        ),
        gecmis_ortalamalar AS (
            SELECT
                sk.kupe_no,
                AVG(sk_eski.sut_miktari) AS ortalama_sut
            FROM son_kayitlar sk
            JOIN LATERAL (
                SELECT sut_miktari
                FROM sagim_kayitlari
                WHERE kupe_no = sk.kupe_no
                  AND id < sk.id
                  AND sagim_zamani = sk.sagim_zamani
                ORDER BY tarih DESC, id DESC
                LIMIT 3
            ) sk_eski ON TRUE
            GROUP BY sk.kupe_no
        )
        SELECT
            i.isim,
            sk.kupe_no,
            sk.tarih,
            sk.sagim_zamani,
            sk.sut_miktari AS son_verim,
            go.ortalama_sut AS eski_ortalama,
            ROUND(((go.ortalama_sut - sk.sut_miktari) / go.ortalama_sut) * 100, 2) AS dusus_yuzdesi,
            COALESCE(i.ciftlik_id, 1) AS ciftlik_id
        FROM son_kayitlar sk
        JOIN gecmis_ortalamalar go ON sk.kupe_no = go.kupe_no
        JOIN inekler i ON sk.kupe_no = i.kupe_no
        WHERE go.ortalama_sut > 0
          AND sk.sut_miktari < go.ortalama_sut * 0.8; 
        """
        
        cursor.execute(query)
        anomalies = cursor.fetchall()
        
        new_alarms_count = 0
        
        for anomaly in anomalies:
            kupe_no = anomaly["kupe_no"]
            tarih = anomaly["tarih"]
            sagim_zamani = anomaly["sagim_zamani"]
            ciftlik_id = anomaly["ciftlik_id"]  # <-- YENİ EKLENEN ALAN
            
            cursor.execute(
                "SELECT id FROM alarmlar WHERE kupe_no = %s AND tarih = %s AND sagim_zamani = %s;",
                (kupe_no, tarih, sagim_zamani)
            )
            exists = cursor.fetchone()
            
            if not exists:
                isim = anomaly["isim"]
                son_verim = float(anomaly["son_verim"])
                eski_ortalama = float(anomaly["eski_ortalama"])
                dusus_yuzdesi = float(anomaly["dusus_yuzdesi"])
                sagim_zamani_tr = "Sabah" if sagim_zamani == 'm' else "Akşam"
                
                print(f"[{kupe_no} - Çiftlik #{ciftlik_id}] - {isim} için anomali tespit edildi. LLM'den mesaj üretiliyor...")

                prompt_template = """
                Sen, çiftçilere yardım eden neşeli ve akıllı yapay zeka asistanı **Süt Sihirbazı**'sın.
                Aşağıdaki bilgilere dayanarak, ineğin süt verimindeki düşüş hakkında çiftçiye samimi, açıklayıcı ve yapıcı bir dille kısa ve net bir uyarı/alarm mesajı yaz. Çiftçiyi paniğe sevk etme, ancak meme sağlığı (mastitis vb.), stres veya yem kontrolü yapmasını tavsiye et.

                İneğin Adı: {isim}
                Küpe Numarası: {kupe_no}
                Sağım Zamanı: {sagim_zamani_tr} ({sagim_zamani})
                Tarih: {tarih}
                Son Sağım Süt Miktarı: {son_verim} litre
                Önceki 3 Sağımın Ortalaması: {eski_ortalama:.1f} litre
                Düşüş Yüzdesi: %{dusus_yuzdesi:.1f}

                Lütfen sadece oluşturduğun alarm mesajını döndür, başka hiçbir şey yazma.
                """
                
                prompt = ChatPromptTemplate.from_template(prompt_template)
                chain = prompt | local_llm | StrOutputParser()
                
                try:
                    mesaj = chain.invoke({
                        "isim": isim,
                        "kupe_no": kupe_no,
                        "sagim_zamani_tr": sagim_zamani_tr,
                        "sagim_zamani": sagim_zamani,
                        "tarih": str(tarih),
                        "son_verim": son_verim,
                        "eski_ortalama": eski_ortalama,
                        "dusus_yuzdesi": dusus_yuzdesi
                    }).strip()
                except Exception as llm_err:
                    print(f"LLM mesaj üretme hatası: {llm_err}")
                    mesaj = f"Dikkat! {isim} ({kupe_no}) isimli ineğinizin {tarih} tarihindeki {sagim_zamani_tr} sağım verimi %{dusus_yuzdesi:.1f} düşmüştür. Son verim: {son_verim} L, Eski Ortalama: {eski_ortalama:.1f} L."

                # YENİ: ciftlik_id ile alarmlar tablosuna kayıt atılıyor
                cursor.execute(
                    """
                    INSERT INTO alarmlar (ciftlik_id, kupe_no, tarih, sagim_zamani, eski_ortalama, son_verim, dusus_yuzdesi, mesaj)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (ciftlik_id, kupe_no, tarih, sagim_zamani, eski_ortalama, son_verim, dusus_yuzdesi, mesaj)
                )
                new_alarms_count += 1
                
                print(f"[{kupe_no}] - Alarm başarıyla oluşturuldu ve veritabanına eklendi.")

                title = f"🚨 {isim} İçin Süt Alarmı!"
                send_push_notification(title, mesaj, data={"highlight_cow": kupe_no, "alert_msg": mesaj, "ciftlik_id": ciftlik_id})
            else:
                print(f"[{kupe_no}] - {tarih} ({sagim_zamani}) zamanlı alarm zaten veritabanında mevcut, atlandı.")
        
        if new_alarms_count > 0:
            conn.commit()
            print(f"Analiz tamamlandı. {new_alarms_count} yeni alarm oluşturuldu ve kaydedildi.")
        else:
            print("Analiz tamamlandı. Yeni süt düşüş alarmı bulunamadı.")
            
        cursor.close()
        return new_alarms_count
    except Exception as e:
        print(f"Süt düşüş analizi hatası: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def generate_daily_summary():
    """
    Günlük toplam süt üretimini dünün üretimiyle kıyaslar, günün en verimli ineğini tespit eder.
    Bunu o gün sağım yapılan HER ÇİFTLİK İÇİN ayrı ayrı hesaplayıp ciftlik_id ile kaydeder.
    """
    print("Günlük çiftlik özetleri üretiliyor...")
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT MAX(tarih) FROM sagim_kayitlari;")
        latest_date_row = cursor.fetchone()
        if not latest_date_row or not latest_date_row[0]:
            print("Veritabanında sağım kaydı bulunamadı.")
            return None
        today_date = latest_date_row[0]
        
        # YENİ: O gün sağımı yapılan tüm çiftlik ID'lerini listeliyoruz
        cursor.execute("SELECT DISTINCT COALESCE(ciftlik_id, 1) FROM sagim_kayitlari WHERE tarih = %s;", (today_date,))
        ciftlik_idler = [row[0] for row in cursor.fetchall()]
        if not ciftlik_idler:
            ciftlik_idler = [1]
        
        cursor.execute("SELECT DISTINCT tarih FROM sagim_kayitlari WHERE tarih < %s ORDER BY tarih DESC LIMIT 1;", (today_date,))
        yesterday_date_row = cursor.fetchone()
        yesterday_date = yesterday_date_row[0] if yesterday_date_row else None
        
        ozet_mesajlari = []

        # YENİ: Her bir çiftlik için özeti döngüyle ayrı hesaplıyoruz
        for c_id in ciftlik_idler:
            cursor.execute("SELECT SUM(sut_miktari) FROM sagim_kayitlari WHERE tarih = %s AND COALESCE(ciftlik_id, 1) = %s;", (today_date, c_id))
            today_total_row = cursor.fetchone()
            today_total = float(today_total_row[0]) if today_total_row and today_total_row[0] is not None else 0.0
            
            yesterday_total = 0.0
            if yesterday_date:
                cursor.execute("SELECT SUM(sut_miktari) FROM sagim_kayitlari WHERE tarih = %s AND COALESCE(ciftlik_id, 1) = %s;", (yesterday_date, c_id))
                yesterday_total_row = cursor.fetchone()
                yesterday_total = float(yesterday_total_row[0]) if yesterday_total_row and yesterday_total_row[0] is not None else 0.0
                
            diff = today_total - yesterday_total
            diff_str = f"+{diff:.1f}" if diff >= 0 else f"{diff:.1f}"
            
            cursor.execute("""
                SELECT i.isim, sk.kupe_no, SUM(sk.sut_miktari) as toplam_sut
                FROM sagim_kayitlari sk
                JOIN inekler i ON sk.kupe_no = i.kupe_no
                WHERE sk.tarih = %s AND COALESCE(sk.ciftlik_id, 1) = %s
                GROUP BY i.isim, sk.kupe_no
                ORDER BY toplam_sut DESC
                LIMIT 1;
            """, (today_date, c_id))
            top_cow_row = cursor.fetchone()
            
            top_cow_name = "Bilinmeyen İnek"
            top_cow_tag = None
            top_cow_milk = 0.0
            if top_cow_row:
                top_cow_name = top_cow_row[0]
                top_cow_tag = top_cow_row[1]
                top_cow_milk = float(top_cow_row[2])
                
            print(f"[Çiftlik #{c_id}] Bugün ({today_date}): {today_total} L. Dün ({yesterday_date}): {yesterday_total} L. En verimli: {top_cow_name} ({top_cow_milk} L).")
            
            mesaj = f"""
            Çiftlik (#{c_id}) Günlük Özeti:
            Bugün({today_date}): {today_total:.1f} L
            Dün({yesterday_date}): {yesterday_total:.1f} L
            Değişim: {diff_str} L
            En verimli: {top_cow_name} ({top_cow_tag}) - {top_cow_milk:.1f} L
            """.strip()

            # YENİ: ciftlik_id filtresi ile mükerrer kontrolü
            cursor.execute(
                "SELECT id FROM gunluk_ozetler WHERE tarih = %s AND COALESCE(ciftlik_id, 1) = %s;",
                (today_date, c_id)
            )
            exists = cursor.fetchone()
            
            if not exists:
                # YENİ: ciftlik_id ile günün özeti kaydediliyor
                cursor.execute(
                    """
                    INSERT INTO gunluk_ozetler (ciftlik_id, tarih, dunku_toplam_sut, bugunku_toplam_sut, en_verimli_inek_kupe_no, mesaj)
                    VALUES (%s, %s, %s, %s, %s, %s);
                    """,
                    (c_id, today_date, yesterday_total, today_total, top_cow_tag, mesaj)
                )
                conn.commit()
                print(f"[{today_date} - Çiftlik #{c_id}] Günlük özet 'gunluk_ozetler' tablosuna başarıyla kaydedildi.")
            else:
                print(f"[{today_date} - Çiftlik #{c_id}] Günlük özet zaten veritabanında mevcut, tekrar kaydedilmedi.")

            title = f"🥛 Günlük Çiftlik Özeti (Çiftlik #{c_id})"
            send_push_notification(title, mesaj, data={"alert_msg": mesaj, "ciftlik_id": c_id})
            ozet_mesajlari.append(mesaj)
            
        return ozet_mesajlari if ozet_mesajlari else None
    except Exception as e:
        print(f"Günlük özet üretme hatası: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

scheduler = BackgroundScheduler(timezone=ZoneInfo("Europe/Istanbul"))

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            func=sagim_verisi_uret_ve_kaydet, 
            trigger='cron', 
            hour=12, 
            minute=0, 
            args=['m'], 
            id='simule_sabah', 
            name='Sentetik Veri Üretimi ve Anomali Tespiti (Sabah 11:30)'
        )
        
        scheduler.add_job(
            func=sagim_verisi_uret_ve_kaydet, 
            trigger='cron', 
            hour=19, 
            minute=0, 
            args=['e'], 
            id='simule_aksam', 
            name='Sentetik Veri Üretimi, Anomali ve Günlük Özet (Akşam 19:00)'
        )
        
        scheduler.start()
        print("Zamanlanmış görev motoru (Scheduler) başlatıldı.")

if __name__ == "__main__":
    os.environ["DB_HOST"] = "localhost" 
    new_alarms_count = check_for_milk_drops()
    print(f"Yeni alarm sayısı: {new_alarms_count}")