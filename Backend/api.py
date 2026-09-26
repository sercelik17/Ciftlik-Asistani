from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, UploadFile, HTTPException, Request, BackgroundTasks,Depends
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, AsyncGenerator, List, Dict, Any
from langchain_core.messages import HumanMessage, ToolMessage, AIMessage
from sql_rag import rag_app
from csv_rag import csv_rag_app
from tool_rag import toolrag_app
from thesis_rag.api_router import create_thesis_router
import uvicorn
import os
from dotenv import load_dotenv
import tempfile
import json
import asyncio
import wave
from groq import Groq
from piper import PiperVoice
from data import sagim_verisi_uret_ve_kaydet
from alarms import start_scheduler,scheduler
from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
import jwt
from fastapi.security import OAuth2PasswordBearer

load_dotenv()
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "super-gizli-sut-sihirbazi-anahtari-12345")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 Günlük token süresi

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

client = Groq(api_key=os.environ.get("WHISPER_API_KEY"))

try:
    voice = PiperVoice.load("tr_TR-dfki-medium.onnx")
except Exception as e:
    print(f"Piper TTS modeli yüklenirken hata oluştu: {e}")
    voice = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Süt Sihirbazı API servisi hazır!")
    
    # 1. Sunucu başlarken zamanlanmış görev motorunu (Scheduler) çalıştır
    start_scheduler() 
    
    yield
    
    # 2. Sunucu kapanırken arka plan görevlerini güvenlice durdur
    print("Süt Sihirbazı API servisi kapanıyor...") #
    if scheduler.running:
        scheduler.shutdown()
        print("Zamanlanmış görev motoru durduruldu.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SignupRequest(BaseModel):
    ciftlik_adi: str
    ad_soyad: str
    eposta: str
    sifre: str
    telefon: Optional[str] = None

class LoginRequest(BaseModel):
    eposta: str
    sifre: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    ciftlik_id: int
    ad_soyad: str

class QueryRequest(BaseModel):
    question: str



class ToolQueryResponse(BaseModel):
    answer: str
    tools_used: List[str] = []
    tool_outputs: List[Dict[str, Any]] = []


class SqlQueryResponse(BaseModel):
    answer: str
    classification: str
    sql_query: Optional[str] = None
    sql_result: Optional[str] = None

class CsvQueryResponse(BaseModel):
    answer: str
    classification: str
    python_code: Optional[str] = None
    raw_result: Optional[str] = None

class TranscriptionResponse(BaseModel):
    text: str
    success: bool

class TtsRequest(BaseModel):
    text: str

class PushTokenRequest(BaseModel):
    token: str

def safe_truncate_password(password: str) -> str:
    """
    Şifreyi UTF-8 byte formatında güvenli bir şekilde maksimum 70 byte'a keser.
    C kütüphanelerinin 72 byte / null terminator sınırına takılmasını %100 engeller.
    """
    return password.encode("utf-8")[:72].decode("utf-8", errors="ignore")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    safe_password = safe_truncate_password(plain_password)
    return pwd_context.verify(safe_password, hashed_password)

def get_password_hash(password: str) -> str:
    safe_password = safe_truncate_password(password)
    return pwd_context.hash(safe_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Kimlik bilgileri doğrulanamadı veya token süresi doldu.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        ciftlik_id: int = payload.get("ciftlik_id")
        
        if user_id is None or ciftlik_id is None:
            raise credentials_exception
            
        return {"user_id": int(user_id), "ciftlik_id": ciftlik_id, "eposta": payload.get("eposta")}
    except jwt.PyJWTError:
        raise credentials_exception

app.include_router(create_thesis_router(get_current_user))

def sse_event(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

def remove_file(path: str):
    if os.path.exists(path):
        os.remove(path)

@app.get("/")
def read_root():
    return {"message": "Süt Sihirbazı API Çalışıyor"}

@app.post("/auth/signup", response_model=TokenResponse)
def signup(request: SignupRequest):
    from alarms import get_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. E-posta kontrolü
        cursor.execute("SELECT id FROM kullanicilar WHERE eposta = %s;", (request.eposta,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Bu e-posta adresi ile kayıtlı bir kullanıcı zaten mevcut.")
        
        # 2. Önce Çiftliği Oluştur ve ID'sini Al
        cursor.execute(
            "INSERT INTO ciftlikler (ciftlik_adi) VALUES (%s) RETURNING id;",
            (request.ciftlik_adi,)
        )
        ciftlik_id = cursor.fetchone()[0]
        
        # 3. Şifreyi Hashle ve Kullanıcıyı Kaydet
        hashed_password = get_password_hash(request.sifre)
        cursor.execute(
            """
            INSERT INTO kullanicilar (ciftlik_id, ad_soyad, eposta, sifre_hash, telefon)
            VALUES (%s, %s, %s, %s, %s) RETURNING id;
            """,
            (ciftlik_id, request.ad_soyad, request.eposta, hashed_password, request.telefon)
        )
        user_id = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        
        # 4. JWT Token Üret
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user_id), "ciftlik_id": ciftlik_id, "eposta": request.eposta},
            expires_delta=access_token_expires
        )
        
        return TokenResponse(
            access_token=access_token,
            ciftlik_id=ciftlik_id,
            ad_soyad=request.ad_soyad
        )

    except HTTPException:
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Kayıt oluşturulurken bir hata oluştu: {str(e)}")
    finally:
        if conn:
            conn.close()

@app.post("/auth/login", response_model=TokenResponse)
def login(request: LoginRequest):
    from alarms import get_db_connection
    from psycopg2.extras import RealDictCursor
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT id, ciftlik_id, ad_soyad, sifre_hash FROM kullanicilar WHERE eposta = %s;",
            (request.eposta,)
        )
        user = cursor.fetchone()
        cursor.close()
        
        if not user or not verify_password(request.sifre, user["sifre_hash"]):
            raise HTTPException(
                status_code=401,
                detail="E-posta adresi veya şifre hatalı.",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user["id"]), "ciftlik_id": user["ciftlik_id"], "eposta": request.eposta},
            expires_delta=access_token_expires
        )
        
        return TokenResponse(
            access_token=access_token,
            ciftlik_id=user["ciftlik_id"],
            ad_soyad=user["ad_soyad"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Giriş yapılırken bir hata oluştu: {str(e)}")
    finally:
        if conn:
            conn.close()

async def tool_query_stream(question: str) -> AsyncGenerator[str, None]:
    yield sse_event({"step": "☁️ Süt Sihirbazı sorunuzu analiz ediyor...", "done": False})
    
    final_answer = ""
    tools_used = []
    tool_outputs = []
    
    try:
        # DÜZELTME 1: rag_app yerine toolrag_app kullanıldı!
        async for output in toolrag_app.astream({"messages": [HumanMessage(content=question)]}, stream_mode="updates"):
            for node_name, state_update in output.items():
                messages = state_update.get("messages", [])
                if not messages:
                    continue
                last_msg = messages[-1]
                
                if node_name == "router":
                    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
                        tool_names = [tc["name"] for tc in last_msg.tool_calls]
                        yield sse_event({"step": f"🛠️ Gerekli araçlar tetikleniyor: {', '.join(tool_names)}", "done": False})
                    else:
                        final_answer = last_msg.content
                        
                elif node_name == "tools":
                    for tool_msg in messages:
                        if isinstance(tool_msg, ToolMessage):
                            tools_used.append(tool_msg.name)
                            tool_outputs.append({"tool": tool_msg.name, "output": tool_msg.content})
                            yield sse_event({"step": f"✅ Veri çekildi: {tool_msg.name}", "done": False})
                            
                elif node_name == "summarizer":
                    yield sse_event({"step": "🔒 Gizlilik Kalkanı (Yerel Model) verileri yorumluyor...", "done": False})
                    final_answer = last_msg.content
                    
                elif node_name == "generate_general_answer":
                    yield sse_event({"step": "☁️ Genel sohbet yanıtı hazırlanıyor...", "done": False})
                    final_answer = last_msg.content
                    
    except Exception as e:
        print(f"Graph çalışma hatası: {e}")
        yield sse_event({"step": "Bir hata oluştu...", "done": True, "answer": f"Üzgünüm, bir hata oluştu: {str(e)}"})
        return

    yield sse_event({
        "done": True,
        "answer": final_answer or "Yanıt oluşturulamadı.",
        "tools_used": tools_used,
        "tool_outputs": tool_outputs
    })

# DÜZELTME 2: EKSİK OLAN STREAMING ENDPOINT ROTA TANIMI EKLENDİ!
@app.post("/query/tool/stream")
async def process_tool_query_stream(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    """Yeni LangGraph araç ajanını (Tool RAG) streaming olarak çalıştırır."""
    return StreamingResponse(
        tool_query_stream(request.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no", 
        }
    )

@app.post("/query/tool/", response_model=ToolQueryResponse)
def process_tool_query(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    """Streaming olmayan standart istekler için Tool RAG endpointi."""
    state = {"messages": [HumanMessage(content=request.question)]}
    
    # DÜZELTME 3: Burada da rag_app yerine toolrag_app kullanıldı!
    final_state = toolrag_app.invoke(state)
    
    messages = final_state["messages"]
    last_message = messages[-1].content
    
    tools_used = []
    tool_outputs = []
    
    for msg in messages:
        if isinstance(msg, ToolMessage):
            tools_used.append(msg.name)
            tool_outputs.append({"tool": msg.name, "output": msg.content})
            
    return ToolQueryResponse(
        answer=last_message,
        tools_used=tools_used,
        tool_outputs=tool_outputs
    )

# === SQL RAG ENDPOINTLERİ ===
async def sql_query_stream(question: str) -> AsyncGenerator[str, None]:
    yield sse_event({"step": "Sorunuz analiz ediliyor...", "done": False})
    
    final_state = {"question": question}
    
    try:
        async for output in rag_app.astream({"question": question}, stream_mode="updates"):
            for node_name, state_update in output.items():
                final_state.update(state_update)
                
                if node_name == "classify":
                    if state_update.get("classification") == "sql":
                        yield sse_event({"step": "Veritabanı için SQL sorgusu oluşturuluyor...", "done": False})
                    else:
                        yield sse_event({"step": "Sihirbaz yanıtı hazırlıyor...", "done": False})
                elif node_name == "write_query":
                    yield sse_event({"step": "Veritabanından veriler alınıyor...", "done": False})
                elif node_name == "execute_query":
                    yield sse_event({"step": "Yanıt doğal dile çevriliyor...", "done": False})
                    
    except Exception as e:
        print(f"Graph çalışma hatası: {e}")
        yield sse_event({"step": "Bir hata oluştu...", "done": True, "answer": "Üzgünüm, işleminizi gerçekleştirirken bir hata oluştu."})
        return

    yield sse_event({
        "done": True,
        "answer": final_state.get("answer", "Yanıt oluşturulamadı."),
        "classification": final_state.get("classification", "general"),
        "sql_query": final_state.get("query"),
        "sql_result": final_state.get("result"),
    })

@app.post("/query/sql/stream")
async def process_query_stream(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    return StreamingResponse(
        sql_query_stream(request.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no", 
        }
    )

@app.post("/query/sql/")
def process_query(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    state = {"question": request.question}
    final_state = rag_app.invoke(state)
    return {
        "answer": final_state["answer"],
        "classification": final_state["classification"],
        "sql_query": final_state.get("query"),
        "sql_result": final_state.get("result"),
    }

# === CSV RAG ENDPOINTLERİ ===
async def csv_query_stream(question: str) -> AsyncGenerator[str, None]:
    yield sse_event({"step": "Soru sınıflandırılıyor...", "done": False})
    await asyncio.sleep(0)

    yield sse_event({"step": "Pandas kodu üretiliyor...", "done": False})
    await asyncio.sleep(0)

    loop = asyncio.get_event_loop()
    state = {"question": question}
    final_state = await loop.run_in_executor(None, csv_rag_app.invoke, state)

    yield sse_event({"step": "Kod çalıştırılıp veri analiz ediliyor...", "done": False})
    await asyncio.sleep(0)

    yield sse_event({"step": "Çiftçi için doğal dilde yanıt hazırlanıyor...", "done": False})
    await asyncio.sleep(0)

    yield sse_event({
        "done": True,
        "answer": final_state.get("answer", "Bir sorun oluştu."),
        "classification": final_state.get("classification", "general"),
        "python_code": final_state.get("python_code"),
        "raw_result": final_state.get("raw_result"),
    })

@app.post("/query/csv/stream")
async def process_csv_query_stream(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    return StreamingResponse(
        csv_query_stream(request.question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )

@app.post("/query/csv/")
def process_csv_query(request: QueryRequest, current_user: dict = Depends(get_current_user)):
    state = {"question": request.question}
    final_state = csv_rag_app.invoke(state)
    return {
        "answer": final_state["answer"],
        "classification": final_state["classification"],
        "python_code": final_state.get("python_code"),
        "raw_result": final_state.get("raw_result"),
    }

# === SES ENDPOINTLERİ ===
@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(audio: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    temp_file_path = None
    try:
        file_ext = os.path.splitext(audio.filename)[1].lower()
        if not file_ext:
            file_ext = ".wav"
            
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            content = await audio.read()
            if not content:
                raise HTTPException(status_code=400, detail="Dosya içeriği boş.")
            temp_file.write(content)
            temp_file_path = temp_file.name

        with open(temp_file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3", 
                file=audio_file,
                language="tr" 
            )

        return TranscriptionResponse(text=transcription.text.strip(), success=True)

    except Exception as e:
        print(f"Hata Detayı: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Transkripsiyon hatası: {str(e)}")
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/tts")
async def text_to_speech(text: str, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    if voice is None:
        raise HTTPException(status_code=500, detail="TTS modeli aktif değil. Lütfen sunucu loglarını kontrol edin.")

    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Metin boş olamaz.")

    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_file_path = temp_file.name
        temp_file.close() 

        with wave.open(temp_file_path, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)

        background_tasks.add_task(remove_file, temp_file_path)

        return FileResponse(
            path=temp_file_path,
            media_type="audio/wav",
            filename="response.wav"
        )

    except Exception as e:
        print(f"TTS Hata Detayı: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Sentezleme hatası: {str(e)}")

# === ALARM & AJANDA ENDPOINTLERİ ===
@app.post("/register-token")
def register_push_token(request: PushTokenRequest, current_user: dict = Depends(get_current_user)):
    token = request.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token boş olamaz.")

    
    from alarms import get_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO cihaz_tokenlari (token) VALUES (%s) ON CONFLICT (token) DO NOTHING;",
            (token,)
        )
        conn.commit()
        cursor.close()
        return {"success": True, "message": "Push token başarıyla kaydedildi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Veritabanı kayıt hatası: {e}")
    finally:
        if conn:
            conn.close()

@app.post("/alarms/check")
def trigger_alarm_check(current_user: dict = Depends(get_current_user)):
    from alarms import check_for_milk_drops
    try:
        new_alarms = check_for_milk_drops()
        return {
            "success": True, 
            "message": f"Süt düşüş analizi tamamlandı. {new_alarms} yeni alarm tespit edildi."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analiz sırasında hata oluştu: {e}")

@app.post("/alarms/daily-summary")
def trigger_daily_summary(current_user: dict = Depends(get_current_user)):
    from alarms import generate_daily_summary
    try:
        summary_msg = generate_daily_summary()
        if summary_msg:
            return {
                "success": True,
                "message": "Günlük özet başarıyla üretildi ve push bildirimi gönderildi.",
                "summary": summary_msg
            }
        else:
            return {
                "success": False,
                "message": "Günlük özet üretilemedi. Kayıt bulunamamış olabilir."
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Özet üretilirken hata oluştu: {e}")

@app.get("/alarms")
def get_alarms(unread_only: bool = False, current_user: dict = Depends(get_current_user)):
    from alarms import get_db_connection
    from psycopg2.extras import RealDictCursor
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if unread_only:
            cursor.execute(
                """
                SELECT a.id, a.kupe_no, i.isim, a.tarih, a.sagim_zamani, a.eski_ortalama, a.son_verim, a.dusus_yuzdesi, a.mesaj, a.okundu, a.olusturulma_tarihi
                FROM alarmlar a
                LEFT JOIN inekler i ON a.kupe_no = i.kupe_no
                WHERE a.okundu = FALSE
                ORDER BY a.tarih DESC, a.id DESC;
                """
            )
        else:
            cursor.execute(
                """
                SELECT a.id, a.kupe_no, i.isim, a.tarih, a.sagim_zamani, a.eski_ortalama, a.son_verim, a.dusus_yuzdesi, a.mesaj, a.okundu, a.olusturulma_tarihi
                FROM alarmlar a
                LEFT JOIN inekler i ON a.kupe_no = i.kupe_no
                ORDER BY a.tarih DESC, a.id DESC;
                """
            )
            
        alarms = cursor.fetchall()
        cursor.close()
        
        for alarm in alarms:
            alarm["tarih"] = str(alarm["tarih"])
            alarm["olusturulma_tarihi"] = str(alarm["olusturulma_tarihi"])
            alarm["eski_ortalama"] = float(alarm["eski_ortalama"])
            alarm["son_verim"] = float(alarm["son_verim"])
            alarm["dusus_yuzdesi"] = float(alarm["dusus_yuzdesi"])
            
        return {"success": True, "alarms": alarms}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alarmlar listelenirken hata oluştu: {e}")
    finally:
        if conn:
            conn.close()

# YENİ ENDPOINT: Sadece Günlük Özetleri Getirir
@app.get("/summaries")
def get_summaries(current_user: dict = Depends(get_current_user)):
    from alarms import get_db_connection
    from psycopg2.extras import RealDictCursor
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT s.id, s.tarih, s.dunku_toplam_sut, s.bugunku_toplam_sut, 
                   s.en_verimli_inek_kupe_no, i.isim as en_verimli_inek_isim, 
                   s.mesaj, s.olusturulma_tarihi
            FROM gunluk_ozetler s
            LEFT JOIN inekler i ON s.en_verimli_inek_kupe_no = i.kupe_no
            ORDER BY s.tarih DESC;
            """
        )
        
        summaries = cursor.fetchall()
        cursor.close()
        
        for summary in summaries:
            summary["tarih"] = str(summary["tarih"])
            summary["olusturulma_tarihi"] = str(summary["olusturulma_tarihi"])
            summary["dunku_toplam_sut"] = float(summary["dunku_toplam_sut"]) if summary["dunku_toplam_sut"] is not None else 0.0
            summary["bugunku_toplam_sut"] = float(summary["bugunku_toplam_sut"]) if summary["bugunku_toplam_sut"] is not None else 0.0
            
        return {"success": True, "summaries": summaries}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Özetler listelenirken hata oluştu: {e}")
    finally:
        if conn:
            conn.close()

@app.post("/alarms/{alarm_id}/read")
def mark_alarm_as_read(alarm_id: int, current_user: dict = Depends(get_current_user)):
    from alarms import get_db_connection
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE alarmlar SET okundu = TRUE WHERE id = %s;", (alarm_id,))
        rows_affected = cursor.rowcount
        conn.commit()
        cursor.close()
        
        if rows_affected == 0:
            raise HTTPException(status_code=404, detail="Alarm bulunamadı.")
            
        return {"success": True, "message": "Alarm okundu olarak işaretlendi."}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Güncelleme hatası: {e}")
    finally:
        if conn:
            conn.close()

@app.post("/simule-data/sabah")
def simule_data_sabah(current_user: dict = Depends(get_current_user)):
    try:
        sagim_verisi_uret_ve_kaydet("m")
        return {"success": True, "message": "Sabah verileri başarıyla üretildi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simülasyon hatası: {e}")

@app.post("/simule-data/aksam")
def simule_data_aksam(current_user: dict = Depends(get_current_user)):
    try:
        sagim_verisi_uret_ve_kaydet("e")
        return {"success": True, "message": "Akşam verileri başarıyla üretildi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simülasyon hatası: {e}")

@app.get("/cows/daily-change")
def get_cows_daily_change(current_user: dict = Depends(get_current_user)):
    from alarms import get_db_connection
    from psycopg2.extras import RealDictCursor
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # En son tarih (bugün) ve bir önceki tarih (dün) bulunarak inek bazlı verimler kıyaslanır
        query = """
        WITH son_tarih AS (
            SELECT MAX(tarih) as bugun FROM sagim_kayitlari
        ),
        onceki_tarih AS (
            SELECT DISTINCT tarih as dun 
            FROM sagim_kayitlari, son_tarih 
            WHERE tarih < son_tarih.bugun 
            ORDER BY tarih DESC 
            LIMIT 1
        ),
        bugun_sut AS (
            SELECT kupe_no, SUM(sut_miktari) as bugun_toplam
            FROM sagim_kayitlari, son_tarih
            WHERE tarih = son_tarih.bugun
            GROUP BY kupe_no
        ),
        dun_sut AS (
            SELECT kupe_no, SUM(sut_miktari) as dun_toplam
            FROM sagim_kayitlari, onceki_tarih
            WHERE tarih = onceki_tarih.dun
            GROUP BY kupe_no
        )
        SELECT 
            i.kupe_no,
            i.isim,
            COALESCE(d.dun_toplam, 0.0) as dunku_sut,
            COALESCE(b.bugun_toplam, 0.0) as bugunku_sut,
            CASE 
                WHEN COALESCE(d.dun_toplam, 0) > 0 THEN 
                    ROUND(((COALESCE(b.bugun_toplam, 0) - d.dun_toplam) / d.dun_toplam * 100)::numeric, 1)
                ELSE 0.0 
            END as degisim_orani
        FROM inekler i
        LEFT JOIN dun_sut d ON i.kupe_no = d.kupe_no
        LEFT JOIN bugun_sut b ON i.kupe_no = b.kupe_no
        ORDER BY degisim_orani DESC, i.isim ASC;;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        cursor.close()
        
        for row in rows:
            row["dunku_sut"] = float(row["dunku_sut"])
            row["bugunku_sut"] = float(row["bugunku_sut"])
            row["degisim_orani"] = float(row["degisim_orani"])
            
        return {"success": True, "data": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Günlük değişim verileri alınırken hata oluştu: {e}")
    finally:
        if conn:
            conn.close()
@app.get("/cows")
def get_cows(current_user: dict = Depends(get_current_user)):
    from alarms import get_db_connection
    from psycopg2.extras import RealDictCursor
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
            i.kupe_no, 
            i.isim,
            COALESCE(avg_tbl.avg_sut, 0.0) as ortalama_sut,
            COALESCE(last_tbl.sut_miktari, 0.0) as son_sut,
            CASE WHEN alarm_tbl.unread_count > 0 THEN 'Riskli' ELSE 'Sağlıklı' END as durum
        FROM inekler i
        LEFT JOIN (
            SELECT kupe_no, ROUND(AVG(sut_miktari)::numeric, 1) as avg_sut
            FROM sagim_kayitlari
            GROUP BY kupe_no
        ) avg_tbl ON i.kupe_no = avg_tbl.kupe_no
        LEFT JOIN (
            SELECT DISTINCT ON (kupe_no) kupe_no, sut_miktari
            FROM sagim_kayitlari
            ORDER BY kupe_no, tarih DESC, id DESC
        ) last_tbl ON i.kupe_no = last_tbl.kupe_no
        LEFT JOIN (
            SELECT kupe_no, COUNT(*) as unread_count
            FROM alarmlar
            WHERE okundu = FALSE
            GROUP BY kupe_no
        ) alarm_tbl ON i.kupe_no = alarm_tbl.kupe_no
        ORDER BY i.isim;
        """
        cursor.execute(query)
        cows = cursor.fetchall()
        cursor.close()
        
        # Tip dönüşümleri
        for cow in cows:
            cow["ortalama_sut"] = float(cow["ortalama_sut"])
            cow["son_sut"] = float(cow["son_sut"])
            
        return {"success": True, "cows": cows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İnek listesi alınırken hata oluştu: {e}")
    finally:
        if conn:
            conn.close()

@app.get("/stats/farm")
def get_farm_stats(days: int = 10, current_user: dict = Depends(get_current_user)):
    from alarms import get_db_connection
    from psycopg2.extras import RealDictCursor
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # LIMIT kısmını dinamik hale getirdik
        query = """
        SELECT tarih, ROUND(SUM(sut_miktari)::numeric, 1) as toplam_sut
        FROM sagim_kayitlari
        GROUP BY tarih
        ORDER BY tarih DESC
        LIMIT %s;
        """
        cursor.execute(query, (days,))
        rows = cursor.fetchall()
        cursor.close()
        
        # Sonuçları kronolojik sıraya sokalım
        rows.reverse()
        
        dates = [str(r["tarih"]) for r in rows]
        yields = [float(r["toplam_sut"]) for r in rows]
        
        return {"success": True, "dates": dates, "yields": yields}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Çiftlik istatistikleri alınırken hata oluştu: {e}")
    finally:
        if conn:
            conn.close()

@app.get("/cows/{kupe_no}/stats")
def get_cow_stats(kupe_no: str, current_user: dict = Depends(get_current_user)):
    from alarms import get_db_connection
    from psycopg2.extras import RealDictCursor
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT tarih, ROUND(SUM(sut_miktari)::numeric, 1) as toplam_sut
        FROM sagim_kayitlari
        WHERE kupe_no = %s
        GROUP BY tarih
        ORDER BY tarih DESC
        LIMIT 10;
        """
        cursor.execute(query, (kupe_no,))
        rows = cursor.fetchall()
        cursor.close()
        
        # Sonuçları kronolojik sıraya sokalım
        rows.reverse()
        
        dates = [str(r["tarih"]) for r in rows]
        yields = [float(r["toplam_sut"]) for r in rows]
        
        return {"success": True, "dates": dates, "yields": yields}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"İnek istatistikleri alınırken hata oluştu: {e}")
    finally:
        if conn:
            conn.close()





if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)