import os
import re
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_ollama import ChatOllama
from langchain_community.utilities import SQLDatabase
from langgraph.graph import START, END, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.prompts import ChatPromptTemplate

# Çevre değişkenlerini yükle
load_dotenv()

# =====================================================================
# 1. VERİTABANI VE LLM BAĞLANTILARI
# =====================================================================
def get_database():
    try:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "Sut_Sihirbazi")
        
        # PostgreSQL bağlantı URI'si
        db_uri = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        return SQLDatabase.from_uri(db_uri, sample_rows_in_table_info=0)
    except Exception as e:
        print(f"❌ Veritabanı bağlantı hatası: {e}")
        return None

db = get_database()

# Bulut modeli: Niyet analizi, tool seçimi (Orkestra Şefi)
cloud_llm = ChatOllama(
    model=os.getenv("CLOUD_LLM", "llama3.2"),
    temperature=0.1,
    num_ctx=2048,
    num_predict=200,
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)

# Yerel model: Veri özetleme ve mahremiyet (Gizlilik Kalkanı)
local_llm = ChatOllama(
    model=os.getenv("LOCAL_LLM", "llama3.2"),
    temperature=0.1,
    num_ctx=2048,
    num_predict=250,
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)

# =====================================================================
# 2. GÜVENLİ VE SABİT TOOLLAR (DETERMİNİSTİK KASLAR)
# =====================================================================
def sanitize_input(text: str) -> str:
    """SQL Injection'a karşı sadece alfanümerik karakterlere ve tireye izin verir."""
    return re.sub(r'[^a-zA-Z0-9-]', '', str(text))

@tool
def get_unread_alarms_tool() -> str:
    """Süt verimi düşen, anomali tespit edilen ineklerin OKUNMAMIŞ acil alarm listesini getirir. 
    'Riskliler', 'sütü düşenler', 'alarmlar', 'hasta inekler' sorulduğunda kullan."""
    if not db: return "Veritabanı bağlantısı yok."
    query = """
    SELECT a.kupe_no, i.isim, a.tarih, a.sagim_zamani, a.eski_ortalama, a.son_verim, a.dusus_yuzdesi, a.mesaj
    FROM alarmlar a LEFT JOIN inekler i ON a.kupe_no = i.kupe_no
    WHERE a.okundu = FALSE ORDER BY a.tarih DESC, a.id DESC LIMIT 10;
    """
    try:
        result = db.run(query)
        return f"Aktif Risk Alarmları: {result}" if result and result != "[]" else "Şu anda okunmamış aktif risk alarmı bulunmuyor."
    except Exception as e: return f"Hata: {e}"

@tool
def get_cow_alarm_history_tool(kupe_no: str) -> str:
    """Belirli bir ineğin (kupe numarası verilen) geçmişteki tüm alarm ve dalgalanma kayıtlarını çeker.
    'Sarıkız'ın neden alarm verdiği', 'geçmiş hastalıkları' sorulduğunda kullan."""
    if not db: return "Veritabanı bağlantısı yok."
    safe_kupe = sanitize_input(kupe_no)
    query = f"SELECT tarih, sagim_zamani, dusus_yuzdesi, mesaj FROM alarmlar WHERE kupe_no = '{safe_kupe}' ORDER BY tarih DESC LIMIT 10;"
    try:
        return f"İnek Alarm Geçmişi: {db.run(query)}"
    except Exception as e: return f"Hata: {e}"

@tool
def get_latest_daily_summary_tool() -> str:
    """Çiftliğin bugünkü toplam süt verimini, dünün üretimiyle kıyaslamasını ve günün şampiyonunu getirir.
    'Bugünkü toplam süt', 'günün özeti', 'durumlar nasıl', 'bugün ne kadar süt sağıldı' sorulduğunda kullan."""
    if not db: return "Veritabanı bağlantısı yok."
    query = """
    SELECT s.tarih, s.dunku_toplam_sut, s.bugunku_toplam_sut, i.isim as en_verimli_inek_isim, s.mesaj
    FROM gunluk_ozetler s LEFT JOIN inekler i ON s.en_verimli_inek_kupe_no = i.kupe_no
    ORDER BY s.tarih DESC LIMIT 1;
    """
    try: return f"Günlük Özet Raporu: {db.run(query)}"
    except Exception as e: return f"Hata: {e}"

@tool
def get_farm_milk_trend_tool(days: int) -> str:
    """Çiftliğin son X günlük toplam süt üretim trendini getirir.
    'Son 10 günlük gidişat', 'üretim grafiği', 'trend' sorulduğunda kullan."""
    if not db: return "Veritabanı bağlantısı yok."
    try:
        safe_days = int(days)
        query = f"SELECT tarih, ROUND(SUM(sut_miktari)::numeric, 1) as toplam_sut FROM sagim_kayitlari GROUP BY tarih ORDER BY tarih DESC LIMIT {safe_days};"
        return f"Son {safe_days} Günlük Üretim Trendi: {db.run(query)}"
    except Exception as e: return f"Hata: {e}"

@tool
def get_cows_daily_change_tool() -> str:
    """Tüm ineklerin dünden bugüne süt üretimindeki değişim oranlarını (%) getirir.
    'Hangi ineğin sütü arttı/azaldı?', 'günlük verim değişim tablosu' sorulduğunda kullan."""
    if not db: return "Veritabanı bağlantısı yok."
    query = """
    WITH son_tarih AS (SELECT MAX(tarih) as bugun FROM sagim_kayitlari),
    onceki_tarih AS (SELECT DISTINCT tarih as dun FROM sagim_kayitlari, son_tarih WHERE tarih < son_tarih.bugun ORDER BY tarih DESC LIMIT 1),
    bugun_sut AS (SELECT kupe_no, SUM(sut_miktari) as bugun_toplam FROM sagim_kayitlari, son_tarih WHERE tarih = son_tarih.bugun GROUP BY kupe_no),
    dun_sut AS (SELECT kupe_no, SUM(sut_miktari) as dun_toplam FROM sagim_kayitlari, onceki_tarih WHERE tarih = onceki_tarih.dun GROUP BY kupe_no)
    SELECT i.kupe_no, i.isim, COALESCE(d.dun_toplam, 0.0) as dunku_sut, COALESCE(b.bugun_toplam, 0.0) as bugunku_sut,
    CASE WHEN COALESCE(d.dun_toplam, 0) > 0 THEN ROUND(((COALESCE(b.bugun_toplam, 0) - d.dun_toplam) / d.dun_toplam * 100)::numeric, 1) ELSE 0.0 END as degisim_orani
    FROM inekler i LEFT JOIN dun_sut d ON i.kupe_no = d.kupe_no LEFT JOIN bugun_sut b ON i.kupe_no = b.kupe_no
    ORDER BY degisim_orani DESC LIMIT 15;
    """
    try: return f"Günlük Verim Değişim Tablosu: {db.run(query)}"
    except Exception as e: return f"Hata: {e}"

@tool
def get_top_producing_cows_tool(limit: int) -> str:
    """Çiftlikteki süt verimi en yüksek şampiyon inekleri getirir.
    'En çok süt veren inekler', 'şampiyonlar', 'elit segment' sorulduğunda kullan."""
    if not db: return "Veritabanı bağlantısı yok."
    try:
        safe_limit = int(limit)
        query = f"""
        SELECT i.kupe_no, i.isim, ROUND(AVG(sk.sut_miktari)::numeric, 1) as ortalama_sut
        FROM sagim_kayitlari sk JOIN inekler i ON sk.kupe_no = i.kupe_no
        GROUP BY i.kupe_no, i.isim ORDER BY ortalama_sut DESC LIMIT {safe_limit};
        """
        return f"En Verimli {safe_limit} İnek: {db.run(query)}"
    except Exception as e: return f"Hata: {e}"

@tool
def get_cow_profile_and_stats_tool(cow_identifier: str) -> str:
    """
    Belirli bir ineğin küpe numarası VEYA ismi ile
    son 10 sağım kaydını getirir.

    Örnek:
    - Serap'ın durumu nasıl?
    - TR0001'in verimi nasıl?
    - Serap'ın süt verimi neden düştü?
    """
    if not db:
        return "Veritabanı bağlantısı yok."

    safe_value = sanitize_input(cow_identifier)

    query = f"""
    SELECT
        i.kupe_no,
        i.isim,
        sk.tarih,
        sk.sagim_zamani,
        sk.sut_miktari
    FROM inekler i
    JOIN sagim_kayitlari sk
        ON i.kupe_no = sk.kupe_no
    WHERE
        i.kupe_no = '{safe_value}'
        OR i.isim ILIKE '%{safe_value}%'
    ORDER BY sk.tarih DESC, sk.id DESC
    LIMIT 10;
    """

    try:
        result = db.run(query)

        if not result or result == "[]":
            return f"{cow_identifier} için sağım kaydı bulunamadı."

        return (
            f"{cow_identifier} için son 10 sağım verisi: "
            f"{result}"
        )

    except Exception as e:
        return f"Hata: {e}"

@tool
def get_cow_latest_milk_drop_tool(cow_identifier: str) -> str:
    """
    İnek ismi veya küpe numarasına göre en son süt düşüş alarmını getirir.
    'Serap'ın sütü neden düştü?', 'Serap ne kadar düşüş yaşadı?',
    'Serap'ın süt verimindeki düşüş' gibi sorularda ÖNCELİKLE kullan.
    """
    if not db:
        return "Veritabanı bağlantısı yok."

    safe_value = sanitize_input(cow_identifier)

    query = f"""
    SELECT
        i.kupe_no,
        i.isim,
        a.tarih,
        a.sagim_zamani,
        a.eski_ortalama,
        a.son_verim,
        a.dusus_yuzdesi
    FROM alarmlar a
    JOIN inekler i
        ON a.kupe_no = i.kupe_no
    WHERE
        i.kupe_no = '{safe_value}'
        OR i.isim ILIKE '%{safe_value}%'
    ORDER BY a.tarih DESC, a.id DESC
    LIMIT 1;
    """

    try:
        result = db.run(query)

        if not result or result == "[]":
            return f"{cow_identifier} için süt düşüş alarmı bulunamadı."

        return (
            f"{cow_identifier} için son süt düşüş alarmı: "
            f"{result}"
        )

    except Exception as e:
        return f"Hata: {e}"    

# =====================================================================
# 3. DİNAMİK SQL ARACI (AD-HOC FALLBACK)
# =====================================================================
@tool
def run_dynamic_sql_tool(query_description: str) -> str:
    """YALNIZCA diğer 7 sabit aracın KAPSAMADIĞI sıradışı sorular için kullan.
    Örnek: 'Mayıs ayında doğan inekler', 'Sabah sağımlarında 15L üstü veren Jersey ırkı'.
    Parametre olarak yapmak istediğin sorgunun tam açıklamasını ver."""
    if not db: return "Veritabanı bağlantısı yok."
    
    sql_prompt = f"""Sen kıdemli bir PostgreSQL mühendisisin. Aşağıdaki şemayı kullanarak istenilen veriyi çekecek SQL sorgusunu yaz.
    ŞEMA: {db.get_table_info()}
    KURALLAR:
    1. Sadece saf SQL sorgusunu döndür (```sql kullanma).
    2. İnek isimleri için KESİNLİKLE 'ILIKE %isim%' kullan.
    3. Sağım zamanı: Sabah='m', Akşam='e'.
    4. KESİNLİKLE sadece SELECT sorgusu yaz. Güncelleme veya silme yapma!
    İstenen Veri: {query_description}
    SQL Sorgusu:"""
    try:
        generated_sql = cloud_llm.invoke(sql_prompt).content.strip().replace("```sql", "").replace("```", "").strip()
        print(f"⚙️ [Dinamik SQL] Üretilen Sorgu: {generated_sql}")
        
        # GÜVENLİK KONTROLÜ: Sadece SELECT sorgularına izin ver
        if not generated_sql.upper().startswith("SELECT"):
            return "Hata: Güvenlik nedeniyle yalnızca SELECT (okuma) sorguları çalıştırılabilir."
            
        result = db.run(generated_sql)
        return f"Özel Sorgu Sonucu: {result}" if result and result != "[]" else "Bu kritere uygun kayıt bulunamadı."
    except Exception as e:
        return f"Özel sorgu hatası: {str(e)}"

# Araç listesi ve bulut modeline bağlanması
tools = [
    get_unread_alarms_tool, 
    get_cow_alarm_history_tool, 
    get_latest_daily_summary_tool,
    get_farm_milk_trend_tool, 
    get_cows_daily_change_tool, 
    get_top_producing_cows_tool,
    get_cow_profile_and_stats_tool, 
    get_cow_latest_milk_drop_tool,
    run_dynamic_sql_tool
]
llm_with_tools = cloud_llm.bind_tools(tools)

# =====================================================================
# 4. LANGGRAPH AJAN VE İŞ AKIŞI (GİZLİLİK KALKANLI)
# =====================================================================
SYSTEM_PROMPT = """Sen Süt Sihirbazı'sın. Çiftçilere yardım eden neşeli, empati yeteneği yüksek uzman bir asistansın.
TÜM YANITLARINI TÜRKÇE VER. İngilizce cevap üretme.
GÖREVLERİN:
1. Veri gerekiyorsa KESİNLİKLE önce 7 sabit araçtan uygun olanı seç.
2. Soru birden fazla adım gerektiriyorsa (Örn: Önce sütü düşenleri bul, sonra o ineklerin küpe numarasıyla alarm geçmişini sorgula), araçları ADIM ADIM sırasıyla çağır.
3. Soru çok sıradışıysa ve sabit araçlar yetmiyorsa 'run_dynamic_sql_tool' kullan.
4. Selamlaşma veya genel sohbetlerde araç çağırma, doğrudan kendin samimi bir dille yanıt ver.
5. Kullanıcı belirli bir ineğin süt düşüşünü, düşüş oranını veya olası nedenlerini soruyorsa önce get_cow_latest_milk_drop_tool aracını kullan. 
Kullanıcı inek ismi verdiyse bunu küpe numarası sanma; araç isim veya küpe numarasını birlikte destekler.
"""

def router_node(state: MessagesState):
    """BULUT MODELİ: Niyet analizi yapar. Gerekirse tool çağırır, gerekmezse doğrudan sohbet eder."""
    messages = state["messages"]
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    
    print("☁️ [ROUTER - BULUT]: Soru analiz ediliyor...")
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

def route_after_llm(state: MessagesState) -> str:
    """Orkestra Şefi (Router) çalıştıktan sonra sıradaki adımı belirler."""
    messages = state["messages"]
    last_msg = messages[-1]
    
    # 1. Durum: LLM yeni bir tool çağırmak istiyor -> 'tools' düğümüne git
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
        
    # 2. Durum: LLM tool çağırmayı bıraktı. Geçmişe bakalım, hiç tool çalışmış mı?
    has_tool_message = any(isinstance(m, ToolMessage) for m in messages)
    
    if has_tool_message:
        # Tool'lar çalışmış, veriler toplanmış -> Yerel Modelle Özetle (Gizlilik Kalkanı)
        return "summarizer"
    else:
        # Hiç tool çalışmadıysa bu sadece bir selamlaşma veya genel sohbettir -> Genel Sohbet
        return "general"

def summarizer_node(state: MessagesState):
    """YEREL MODEL (GİZLİLİK KALKANI): Veritabanından gelen ham veriyi lokalde çiftçi için yorumlar."""
    messages = state["messages"]
    
    user_question = ""
    tool_data = ""
    
    for msg in messages:
        if isinstance(msg, HumanMessage):
            user_question = msg.content
        elif isinstance(msg, ToolMessage):
            tool_data += f"- {msg.name}: {msg.content}\n"
    summarizer_prompt = f"""Sen Süt Sihirbazı'sın. Çiftçinin sorusunu, veritabanından çekilen aşağıdaki verileri kullanarak samimi ve net bir dille cevapla.

            DİL KURALI:
            - HER ZAMAN TÜRKÇE CEVAP VER.
            - Kullanıcı hangi dilde sorarsa sorsun yanıt dili Türkçe olmalıdır.
            - İngilizce başlık, açıklama veya ifade kullanma.
            - Veritabanından gelen sayısal değerleri değiştirme veya uydurma.
            
            KRİTİK KURAL VE YORUMLAMA REHBERİ:
            1. 'get_cow_alarm_history_tool' veya 'get_unread_alarms_tool' tarafından döndürülen her mesaj bir "RİSK ALARMI" kaydıdır.
            2. Mesajların içindeki "meme sağlığı", "mastitis", "stres" veya "süt düşüşü" uyarılarını o ineğin geçmiş risk alarmı / olası hastalık şüphesi olarak kabul et ve çiftçiye özetle.
            3. Sadece ve sadece araçlardan GEREKLİ HİÇBİR VERİ DÖNMEDİYSE "Bu konuda bilgi çekilemedi" de. Veri varsa mutlaka listele veya tablo halinde sun.

            Verileri okunaklı listeler veya küçük tablolar halinde sun.
            Ham SQL veya teknik terimler kullanma.

            Çiftçinin Sorusu: {user_question}

            Veritabanı Sonuçları:
            {tool_data}

            Cevabın:"""
    
    print("🔒 [GİZLİLİK KALKANI - YEREL]: Veriler lokalde yorumlanıyor...")
    response = local_llm.invoke(summarizer_prompt)
    return {"messages": [response]}

def generate_general_answer(state: MessagesState):
    """BULUT MODELİ: Tool gerektirmeyen selamlaşma ve genel sohbetler için 
    yalın bulut modeliyle doğrudan samimi ve neşeli bir cevap üretir."""
    messages = state["messages"]
    
    # Kullanıcının son sorusunu/mesajını bulalım
    user_question = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            user_question = msg.content
            break
    
    print("☁️ [GENEL SOHBET - BULUT]: Tool gerekmeyen sohbet cevaplanıyor...")
    
    # Genel sohbet için tool tanımları İÇERMEYEN neşeli bir prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Sen Süt Sihirbazı'sın. Çiftçilere yardım eden neşeli, empati yeteneği yüksek uzman bir asistansın. HER ZAMAN TÜRKÇE cevap ver. İngilizce cevap üretme. Çiftçinin selamını veya genel sorusunu samimi, doğal ve yardımsever bir dille cevapla."),
        ("human", "{question}")
    ])
    
    # Dikkat: Burada llm_with_tools DEĞİL, yalın cloud_llm kullanıyoruz
    chain = prompt | cloud_llm
    response = chain.invoke({"question": user_question})
    
    return {"messages": [response]}

# LangGraph Düğümleri ve Kenarları
# Düğümleri grafiğe ekle
# LangGraph Düğümleri ve Kenarları
tool_node = ToolNode(tools)

workflow = StateGraph(MessagesState)
workflow.add_node("router", router_node)
workflow.add_node("tools", tool_node)
workflow.add_node("summarizer", summarizer_node)
workflow.add_node("generate_general_answer", generate_general_answer)

workflow.add_edge(START, "router")

# Kendi akıllı yönlendiricimizi kullanıyoruz:
workflow.add_conditional_edges(
    "router",
    route_after_llm,
    {
        "tools": "tools",
        "summarizer": "summarizer",
        "general": "generate_general_answer"
    }
)

# --- İŞTE SİHRİN GERÇEKLEŞTİĞİ YER ---
# Tool çalıştıktan sonra akışı bitirme veya özetleyiciye atma!
# Veriyi değerlendirmesi ve gerekiyorsa YENİ TOOL çağırması için ROUTER'A GERİ GÖNDER!
workflow.add_edge("tools", "router") 

workflow.add_edge("summarizer", END)
workflow.add_edge("generate_general_answer", END)

toolrag_app = workflow.compile()

if __name__ == "__main__":
    png_bytes = toolrag_app.get_graph().draw_mermaid_png()

    with open("toolrag_app.png", "wb") as f:
        f.write(png_bytes)

    print("toolrag_app.png oluşturuldu.")

