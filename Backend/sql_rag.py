from langchain_ollama import ChatOllama
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from typing_extensions import TypedDict
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langgraph.graph import START, END, StateGraph
import os 
from dotenv import load_dotenv
import time
load_dotenv()

# --- YARDIMCI FONKSİYONLAR ---

def get_database():
    try:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME")
        db_uri = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        db = SQLDatabase.from_uri(db_uri,sample_rows_in_table_info=0)
        return db
    except Exception as e:
       print(f"Veritabanı bağlantı hatası: {e}")
       return None

db = get_database()
cloud_llm = ChatOllama(
    model=os.getenv("CLOUD_LLM"),
    temperature=0.7, 
    base_url=os.getenv("OLLAMA_BASE_URL")
)
local_llm = ChatOllama(
    model=os.getenv("LOCAL_LLM"),
    temperature=0.1, 
    base_url=os.getenv("OLLAMA_BASE_URL")
)

# --- DURUM (STATE) TANIMI ---

class State(TypedDict):
    question: str
    classification: str 
    query: str
    result: str
    answer: str
 

# --- DÜĞÜMLER (NODES) ---

def classify_input(state: State):
    initial_retry = 0
    router_prompt = """
    Sen, bir çiftlik yönetim sistemi için akıllı yönlendirme asistanısın. Görevin, gelen soruyu analiz ederek cevabın bulunabileceği en doğru teknik katmanı seçmektir. Karar verirken şu kuralları uygula:
    
    **1.SQL (Veri & Kayıt Sorguları):** Eğer soru; isim (örn: "Sarıkız"), küpe numarası, miktar, tarih, istatistik veya belirli bir hayvana/gruba ait güncel durumu (süt verimi, konum, yaş) sorguluyorsa bu kategoriyi seç.
    **Kritik Belirteç:** "Kaç tane?", "Ne zaman?", "Kim?", "Nerede?" soruları ve özel isim/ID içeren tüm sorgular.

    

    **2.GENERAL (Genel Sohbet):** Selamlaşma, sistemin kapasitesini sorma veya çiftlik operasyonlarıyla ilgisi olmayan rastgele sohbetler.
    **Ayırıcı Kural:** Cevap bir tabloda/hücrede tutulan bir veri mi (SQL), yoksa bir dökümanda/kitapta anlatılan bir konu mu (RAG)?
    
    Sadece "SQL" veya "GENERAL" kelimesini döndür.
    
    Soru: {question}

     -- CEVAP ÖRNEKLERİ --
    Soru:"Çiftlikteki Jersey ırkı ineklerin sayısı nedir?",
    Cevap: SQL

    """
    prompt = ChatPromptTemplate.from_template(router_prompt)
    chain = prompt | cloud_llm | StrOutputParser()
    
    response = chain.invoke({"question": state["question"]})
    decision = response.strip().upper()
    
    # Güvenlik kontrolü
    if "SQL" in decision: return {"classification": "sql","retry_count": initial_retry}
    
    return {"classification": "general","retry_count": initial_retry}

def write_query(state: State):
    # Denetleyiciden gelen bir hata mesajı varsa, bunu modele iletmek için hazırlıyoruz
    error_feedback_text = ""
    if state.get("feedback") and state["feedback"] != "CORRECT":
        error_feedback_text = f"\n\n--- ÖNEMLİ: ÖNCEKİ HATANIN DÜZELTİLMESİ ---\nSon ürettiğin sorgu şu hatayı verdi: {state['feedback']}\nLütfen bu hatayı analiz et ve doğru sorguyu tekrar üret."

   
    system_prompt = """
    Sen PostgreSQL konusunda uzmanlaşmış, kıdemli bir Veritabanı Mühendisisin.
    Görevin: Çiftçinin doğal dilde sorduğu soruları, aşağıdaki şemaya uygun, en optimize ve hatasız SQL sorgularına çevirmektir.

    --- VERİTABANI ŞEMASI ---
    {table_info}{error_feedback}

    --- KESİN KURALLAR ---
    1. Sadece geçerli PostgreSQL sorgusu döndür.
    2. Markdown kod bloklarını (```sql ... ```) kullanma, sadece ham metin olarak sorguyu yaz.
    3. Çıktıda SQL dışında tek bir karakter bile olmamalıdır.
    4.Veritabanındaki bütün inek isimleri küçük harflerle kaydedilmiştir. Bu nedenle, filtreleme yaparken büyük/küçük harf duyarlılığına dikkat et ve gerektiğinde 'ILIKE' kullan.
    4. METİN ARAMALARI: Metin tabanlı filtrelemelerde (özellikle inek isimleri aranırken) büyük/küçük harf duyarlılığını önlemek için '=' veya 'LIKE' yerine KESİNLİKLE 'ILIKE%isim%' operatörünü kullan. 
    5. VERİ STANDARDI: Sağım zamanı sorgulanırken Sabah sağımı için 'm', Akşam sağımı için 'e' değerleri aranmalıdır. Filtrelemelerde (WHERE koşullarında) asla "sabah" veya "akşam" kelimelerini kullanma, kesinlikle 'm' ve 'e' karakterlerini kullan.
    


   
    """
    
    query_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt), 
        ("user", "Soru: {input}")
    ])
    
    chain = query_prompt | cloud_llm | StrOutputParser()
    
    result = chain.invoke({
        "table_info": db.get_table_info(), 
        "error_feedback": error_feedback_text,
        "input": state["question"]
    })
    
    # Markdown temizliği ve gereksiz boşlukların alınması
    clean_query = result.strip().replace("```sql", "").replace("```", "").strip()
    
    return {"query": clean_query}



def execute_query(state: State):
    execute_tool = QuerySQLDatabaseTool(db=db)
    return {"result": execute_tool.invoke(state["query"])}
    

def generate_sql_answer(state: State):
    # Boş sonuç kontrolü — LLM'e bırakma
    result = state["result"]
    if not result or result in [[], [[]], "", "[]", None]:
        return {"answer": "Üzgünüm, aradığınız kritere uygun bir kayıt bulunamadı."}

    prompt_template = """Sen bir çiftlik yönetim asistanısın.

Aşağıdaki veritabanı sorgu sonucunu çiftçinin anlayacağı doğal Türkçeye çevir.

Kurallar:
- Ham veri, sütun adı veya teknik terim kullanma
- Sayıları bağlamıyla yaz ("42 inek", sadece "42" değil)
- Kısa ve tek paragraf yaz
- gerekirse elindeki veriyi tablo şeklinde sunabilirsin ama sadece kritik bilgileri içermeli, tüm ham sonuçları değil
- Liste veya madde işareti kullanma

Örnekler:
Soru: Kaç ineğim var?
Sonuç: [(42,)]
Yanıt: Çiftliğinizde şu an toplam 42 inek bulunmaktadır.

Soru: En son sağılan ineğin adı ne?
Sonuç: [('Sarıkız', 18.5, '2024-01-15')]
Yanıt: En son 15 Ocak 2024 tarihinde sağılan ineğiniz Sarıkız olup 18.5 litre süt vermiştir.

Soru: Tüm ineklerin süt ortalaması nedir?
Sonuç: [('Sarıkız', 18.5), ('Benekli', 22.0), ('Karabaş', 15.3)]
Yanıt: İneklerinizin günlük ortalama süt üretimleri aşağıdaki gibidir:

| İnek Adı | Ortalama Süt (litre) |
|----------|----------------------|
| Sarıkız  | 18.5                 |
| Benekli  | 22.0                 |
| Karabaş  | 15.3                 |

---
Soru: {question}
Sonuç: {result}
Yanıt:"""

    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | local_llm | StrOutputParser()
    response = chain.invoke({"question": state["question"], "result": result})

    return {"answer": response.strip()}


# --- RAG VE GENERAL DÜĞÜMLERİ ---



def generate_general_answer(state: State):
    prompt_template = """
    Sen **Süt Sihirbazı**'sın. Çiftçilere yardım eden neşeli bir yapay zeka asistanısın.
    Soru: {question}
    Samimi, yardımsever bir dille cevap ver.
    """
    prompt = ChatPromptTemplate.from_template(prompt_template)
    chain = prompt | cloud_llm | StrOutputParser()
    response = chain.invoke({"question": state["question"]})
    return {"answer": response}


# --- KOŞULLU YÖNLENDİRME MANTIĞI ---



# --- GRAFİK YAPISI ---

workflow = StateGraph(State)

workflow.add_node("classify", classify_input)
workflow.add_node("write_query", write_query)
workflow.add_node("execute_query", execute_query)
workflow.add_node("generate_sql_answer", generate_sql_answer)
workflow.add_node("generate_general_answer", generate_general_answer)

workflow.add_edge(START, "classify")

workflow.add_conditional_edges(
    "classify",
    lambda x: x["classification"],
    {"sql": "write_query", "general": "generate_general_answer"}
)

workflow.add_edge("write_query", "execute_query")
workflow.add_edge("execute_query", "generate_sql_answer")
workflow.add_edge("generate_sql_answer", END)
workflow.add_edge("generate_general_answer", END)

rag_app = workflow.compile()




