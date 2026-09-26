from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from .farm_adapter import FarmDataService
from .query_router import QueryRouter
from .rag_chain import RAGService
from .settings import settings


class ThesisAssistantService:
    """SQL + Hybrid RAG + LangChain router orkestrasyonu."""

    def __init__(self):
        self.router = QueryRouter()
        self.rag = RAGService()
        self.farm = FarmDataService()
        self.local_llm = ChatOllama(
            model=settings.rag_llm,
            temperature=0.1,
            base_url=settings.ollama_base_url,
        )
        self.hybrid_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """Sen hayvancılık karar-destek asistanısın.

Elinde iki ayrı veri türü vardır:

1. ÇİFTLİK VERİSİ:
Kullanıcının kendi PostgreSQL kayıtlarından elde edilmiştir.
Bu verilerde bulunan isim, tarih, süt miktarı, yüzde değişim, alarm ve diğer sayısal değerleri AYNEN kullan.
Çiftlik verisinde bulunmayan bir sayıyı veya olayı uydurma.

2. KAYNAK BAĞLAMI:
RAG sistemi tarafından güvenilir dokümanlardan getirilen bilgidir.
Dokümanlardan gelen her sağlık veya teknik iddianın sonunda mutlaka [K1], [K2] gibi kaynak etiketi kullan.

YANIT KURALLARI:
- HER ZAMAN TÜRKÇE cevap ver.
- Önce çiftlik kayıtlarında görülen SOMUT BULGUYU açıkla.
- Çiftlik verisinde sayısal değer varsa mutlaka cevaba dahil et.
- Sonra bu bulgunun olası nedenlerini yalnızca KAYNAK BAĞLAMI üzerinden açıkla.
- Kaynakta geçmeyen hastalık, stres, besleme problemi veya başka bir nedeni uydurma.
- Çiftlik alarm mesajında bir ihtimal yazıyor fakat RAG kaynağı bunu desteklemiyorsa, bunu kesin neden gibi sunma.
- Süt verimindeki düşüşü tek başına hastalık tanısı olarak yorumlama.
- Kesin veteriner tanısı koyma.
- Gerektiğinde veteriner hekim değerlendirmesi öner.
- Kaynak etiketlerini yalnızca KAYNAK BAĞLAMI içindeki etiketlerden kullan.
- Kısa, açık ve bilimsel olarak temkinli yanıt ver.
- Kullanıcı sorusunda geçen hayvan ismi kullanıcı adı değildir. Hayvan adına "Merhaba" diye hitap etme.
- ÇİFTLİK VERİSİNDE bulunan mastitis, stres veya başka bir olası neden ifadesini bilimsel gerçek kabul etme. Sağlıkla ilgili nedenleri yalnızca KAYNAK BAĞLAMI üzerinden açıkla.

Yanıt düzeni:
1. Çiftlik verisindeki bulgu
2. Kaynaklara göre olası açıklama
3. Kısa değerlendirme / öneri
""",
    ),
    (
        "human",
        """KULLANICI SORUSU:
{question}

ÇİFTLİK VERİSİ:
{farm_context}

KAYNAK BAĞLAMI:
{rag_context}

Birleştirilmiş yanıt:""",
    ),
])
        self.hybrid_chain = self.hybrid_prompt | self.local_llm

    def ask(self, question: str, ciftlik_id: int | None = None) -> dict[str, Any]:
        route = self.router.classify(question)

        if route == "SQL":
            answer = self.farm.answer(question)
            return {"route": route, "answer": answer, "sources": []}

        if route == "RAG":
            result = self.rag.answer(question)
            return {"route": route, **result}

        if route == "HYBRID":

            # 1. Gerçek çiftlik verisini doğrudan PostgreSQL'den getir
            farm_data = self.farm.get_latest_milk_drop(
                question=question,
                ciftlik_id=ciftlik_id,
            )

            # 2. RAG tarafında uzmanlık bilgisini ve kaynakları getir
            rag_question = (
                "Süt sığırlarında ani süt verimi düşüşü mastitis veya meme sağlığı "
                "sorunlarıyla nasıl ilişkili olabilir? "
                "Yalnızca süt verimi düşüşüyle doğrudan ilişkili bilgileri belirt. "
                "Belirli bir hayvanda kesin neden veya tanı ileri sürme."
            )

            rag_result = self.rag.answer(rag_question)

            # 3. Çiftlik verisini LLM'e yazdırmıyoruz.
            # Sayısal değerleri Python deterministik olarak oluşturuyor.
            if farm_data:

                sagim_zamani = (
                    "akşam"
                    if farm_data["sagim_zamani"] == "e"
                    else "sabah"
                )

                tarih = farm_data["tarih"].strftime("%d.%m.%Y")

                eski_ortalama = (
                    f'{farm_data["eski_ortalama"]:.2f}'
                    .replace(".", ",")
                )

                son_verim = (
                    f'{farm_data["son_verim"]:.2f}'
                    .replace(".", ",")
                )

                dusus_yuzdesi = (
                    f'{farm_data["dusus_yuzdesi"]:.2f}'
                    .replace(".", ",")
                )

                farm_answer = (
                    f'Çiftlik kayıtlarına göre {farm_data["isim"]} '
                    f'({farm_data["kupe_no"]}) için {tarih} tarihli '
                    f'{sagim_zamani} sağımında süt verimi, '
                    f'önceki sağım ortalaması olan {eski_ortalama} litreden '
                    f'{son_verim} litreye düşmüştür. '
                    f'Bu değişim yaklaşık %{dusus_yuzdesi} oranında '
                    f'bir süt verimi düşüşüne karşılık gelmektedir.'
                )

            else:
                farm_answer = (
                    "Çiftlik kayıtlarında bu soruyla ilişkilendirilebilecek "
                    "sayısal bir süt düşüş kaydı bulunamadı."
                )

            # 4. Kesin çiftlik bulgusu + kaynaklı RAG cevabı
            answer = (
                f"{farm_answer}\n\n"
                f"Kaynaklara göre genel değerlendirme:\n"
                f"{rag_result['answer']}\n\n"
                f"Bu kaynak bilgileri Serap için kesin bir neden veya tanı göstermez. "
                f"Süt verimindeki düşüşün nedeni, diğer klinik bulgular ve hayvanın "
                f"genel durumu birlikte değerlendirilerek belirlenmelidir."
            )

            return {
                "route": route,
                "answer": answer,
                "sources": rag_result["sources"],
            }

        # CHAT
        response = self.local_llm.invoke(
            "Sen hayvancılık alanında çalışan yardımsever bir asistansın. "
            "Kullanıcının aşağıdaki kısa sohbet mesajına doğal ve kısa Türkçe cevap ver: "
            + question
        )
        return {"route": route, "answer": response.content, "sources": []}
