"""REST endpoints for the SAP help corpus and the ask flow."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.dependencies import get_help_assistant, get_help_repository
from app.models.chat import AskRequest, AskResponse
from app.repositories.help_repository import HelpRepository
from app.services.claude_service import ClaudeServiceError
from app.services.help_assistant import HelpAssistant

router = APIRouter(prefix="/api/help", tags=["help"])

RepositoryDep = Annotated[HelpRepository, Depends(get_help_repository)]
AssistantDep = Annotated[HelpAssistant, Depends(get_help_assistant)]


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, assistant: AssistantDep) -> AskResponse:
    """Answer a question.

    Claude first decides whether SAP Help Portal content is needed. When it
    returns `needed_for_help_input`, the `help` collection is searched with the
    queries Claude proposed and the answer is written from those documents;
    otherwise Claude's direct answer is returned unchanged.
    """
    try:
        return await assistant.ask(request)
    except ClaudeServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # surface the cause instead of a bare 500
        raise HTTPException(status_code=500, detail=f"Ask failed: {exc}") from exc


@router.get("/documents")
async def list_documents(
    repository: RepositoryDep,
    product_id: Annotated[str | None, Query(description="Filter by SAP product id")] = None,
    document_type: Annotated[str | None, Query(description="Filter by document type")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """Page through the indexed help topics, newest publication first."""
    documents = await repository.list(
        product_id=product_id, document_type=document_type, skip=skip, limit=limit
    )
    total = await repository.count(product_id=product_id, document_type=document_type)
    return {"total": total, "skip": skip, "limit": limit, "documents": documents}


@router.get("/documents/{document_id}")
async def get_document(
    repository: RepositoryDep,
    document_id: Annotated[str, Path(description="`<loio>:<language>`, e.g. 496d…:en-US")],
) -> dict[str, Any]:
    """Fetch one help topic by id."""
    document = await repository.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"No help document {document_id!r}")
    return document


@router.get("/search")
async def search_documents(
    repository: RepositoryDep,
    q: Annotated[str, Query(min_length=1, description="Full-text query")],
    product: Annotated[list[str] | None, Query(description="Repeatable product filter")] = None,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> dict[str, Any]:
    """Full-text search the help collection directly, without involving Claude."""
    documents = await repository.search(q, products=product, limit=limit)
    return {"query": q, "count": len(documents), "documents": documents}


@router.get("/products")
async def list_products(repository: RepositoryDep) -> dict[str, Any]:
    """Product facets, largest first."""
    products = await repository.products()
    return {"count": len(products), "products": products}


@router.get("/stats")
async def stats(repository: RepositoryDep) -> dict[str, Any]:
    """Corpus size plus the product and document-type facets."""
    return {
        "documents": await repository.count(),
        "products": await repository.products(limit=10),
        "document_types": await repository.document_types(limit=10),
    }
