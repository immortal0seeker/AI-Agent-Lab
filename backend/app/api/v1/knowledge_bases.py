from uuid import UUID

from fastapi import APIRouter, Depends, Response, status

from app.api.dependencies import get_knowledge_base_service
from app.schemas import (
    KnowledgeBaseCreate,
    KnowledgeBaseRead,
    KnowledgeBaseUpdate,
)
from app.services import KnowledgeBaseService


router = APIRouter(
    prefix="/knowledge-bases",
    tags=["knowledge-bases"],
)


@router.get("", response_model=list[KnowledgeBaseRead])
def list_knowledge_bases(
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
) -> list[KnowledgeBaseRead]:
    return [
        KnowledgeBaseRead.model_validate(row)
        for row in service.list_knowledge_bases()
    ]


@router.post(
    "",
    response_model=KnowledgeBaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge_base(
    data: KnowledgeBaseCreate,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
) -> KnowledgeBaseRead:
    return KnowledgeBaseRead.model_validate(
        service.create_knowledge_base(data)
    )


@router.get(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseRead,
)
def get_knowledge_base(
    knowledge_base_id: UUID,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
) -> KnowledgeBaseRead:
    return KnowledgeBaseRead.model_validate(
        service.get_knowledge_base(knowledge_base_id)
    )


@router.patch(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseRead,
)
def update_knowledge_base(
    knowledge_base_id: UUID,
    data: KnowledgeBaseUpdate,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
) -> KnowledgeBaseRead:
    return KnowledgeBaseRead.model_validate(
        service.update_knowledge_base(knowledge_base_id, data)
    )


@router.delete(
    "/{knowledge_base_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_knowledge_base(
    knowledge_base_id: UUID,
    service: KnowledgeBaseService = Depends(
        get_knowledge_base_service
    ),
) -> Response:
    service.delete_knowledge_base(knowledge_base_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
