from thesis_rag.rag_chain import RAGService

rag = RAGService()

questions = [

    ("03_besleme",
    "Yetersiz kuru madde tüketimi süt ineklerinde süt verimini nasıl etkileyebilir?"),
]

for category, question in questions:
    print("\n" + "=" * 80)
    print("KATEGORİ:", category)
    print("SORU:", question)
    print("=" * 80)

    result = rag.answer(question)

    print("\nCEVAP:")
    print(result["answer"])

    print("\nKAYNAKLAR:")

    if not result["sources"]:
        print("Kaynak bulunamadı.")

    for source in result["sources"]:
        print(
            f"- [{source['id']}] "
            f"{source['title']} | "
            f"Sayfa: {source['page']} | "
            f"Skor: {source['score']}"
        )