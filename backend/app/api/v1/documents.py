from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.dependencies import get_document_service
from app.schemas import DocumentRead
from app.services import DocumentService

router = APIRouter(tags=["documents"])


@router.post(
    "/knowledge-bases/{knowledge_base_id}/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    knowledge_base_id: UUID,
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
) -> DocumentRead:
    document = await service.upload_document(
        knowledge_base_id,
        original_filename=file.filename,
        stream=file,
    )
    return DocumentRead.model_validate(document)
