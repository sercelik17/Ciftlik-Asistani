"""Hayvancılık tez projesi için LangChain + Hybrid RAG katmanı."""

__all__ = ["ThesisAssistantService"]


def __getattr__(name: str):
    if name == "ThesisAssistantService":
        from .thesis_service import ThesisAssistantService
        return ThesisAssistantService
    raise AttributeError(name)
