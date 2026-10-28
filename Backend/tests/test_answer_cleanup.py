from thesis_rag.answer_cleanup import INSUFFICIENT, finish_answer
from thesis_rag.chunk_filter import is_low_value_chunk
from thesis_rag.settings import settings


def test_drops_truncated_english_tail():
    raw = (
        "Mastitis süt kalitesini düşürür. "
        "The importance of somatic cell count (SCC) in herd udder health "
        "management is highlighted, particularly in the dairy"
    )
    cleaned = finish_answer(raw)
    assert "süt kalitesini" in cleaned
    assert "highlighted" not in cleaned
    assert cleaned.endswith(".")


def test_empty_after_filter_says_insufficient():
    assert finish_answer("The cow is likely to") == INSUFFICIENT


def test_bibliography_chunk_is_low_value():
    text = (
        "Bibliography Carvalho, P. D. et al. 2015. J. Dairy Sci. 98:8741. "
        "Moreira, F. et al. 2000. J. Anim. Sci. 78:1568. "
        "Martins, J. P. N. et al. 2018. J. Dairy Sci. 101."
    )
    assert is_low_value_chunk(text)
    assert not is_low_value_chunk(
        "Lactating dairy cows must consume large quantities of dry matter "
        "to maintain high levels of milk production and reproductive performance."
    )


def test_generation_window_allows_complete_sentences():
    assert settings.llm_num_predict >= 400
    assert settings.llm_num_ctx >= 4096
