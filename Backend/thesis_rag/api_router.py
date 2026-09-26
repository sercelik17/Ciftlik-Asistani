from __future__ import annotations

import traceback
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .thesis_service import ThesisAssistantService


class ThesisQueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class ThesisQueryResponse(BaseModel):
    route: str
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)


_service: ThesisAssistantService | None = None


def get_service() -> ThesisAssistantService:
    global _service

    if _service is None:
        _service = ThesisAssistantService()

    return _service


def create_thesis_router(auth_dependency: Callable) -> APIRouter:
    router = APIRouter(
        prefix="/query/thesis",
        tags=["Thesis RAG"],
    )

    @router.get("/health")
    def health():
        return {
            "status": "ok",
            "module": "LangChain + BM25 + FAISS Hybrid RAG",
        }

    @router.post("/", response_model=ThesisQueryResponse)
    def query_thesis(
        request: ThesisQueryRequest,
        current_user: dict = Depends(auth_dependency),
    ):
        try:
            result = get_service().ask(
                question=request.question,
                ciftlik_id=current_user.get("ciftlik_id"),
            )

            return ThesisQueryResponse(**result)

        except FileNotFoundError as exc:
            traceback.print_exc()

            raise HTTPException(
                status_code=503,
                detail=str(exc),
            ) from exc

        except Exception as exc:
            traceback.print_exc()

            raise HTTPException(
                status_code=500,
                detail=f"Tez RAG servisi hatası: {exc}",
            ) from exc

    return router