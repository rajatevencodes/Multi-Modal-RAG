from fastapi import APIRouter, HTTPException, Depends
from src.services.supabase import supabase
from src.services.clerkAuth import get_current_user_clerk_id
from src.services.awsS3 import s3_client
from src.config.index import appConfig
from src.models.index import FileUploadRequest, UrlRequest, ProcessingStatus
from src.utils.index import validate_url
import uuid
from src.services.celery import perform_rag_ingestion_task
from src.config.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["projectFilesRoutes"])

"""
`/api/project`

    GET `/{project_id}/files` - Get project files: 
    Generate presigned url for file upload for frontend: POST `/{project_id}/files/get-presigned-url`
    POST `/{project_id}/files/confirm-upload-to-s3` : Confirmation of file upload to S3
    POST `/{project_id}/files/process-url` : Add website URL to database
    DELETE `/{project_id}/files/delete/{document_id}` : Delete project document
    GET `{project_id}/files/{document_id}/chunks` : Get project document chunks
"""


@router.get("/{project_id}/files")
async def get_project_files(
    project_id: str, current_user_clerk_id: str = Depends(get_current_user_clerk_id)
):
    try:
        logger.info("get_project_files_started", project_id=project_id)
        project_files_result = (
            supabase.table("project_documents")
            .select("*")
            .eq("project_id", project_id)
            .eq("clerk_id", current_user_clerk_id)
            .order("created_at", desc=True)
            .execute()
        )

        logger.info(
            "get_project_files_success",
            project_id=project_id,
            count=len(project_files_result.data),
        )
        return {
            "success": True,
            "message": "Project files retrieved successfully",
            "data": project_files_result.data,
        }
    except Exception as e:
        logger.error(
            "get_project_files_exception",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while retrieving project {project_id} files: {str(e)}",
        )


@router.post("/{project_id}/files/get-presigned-url")
async def get_upload_presigned_url(
    project_id: str,
    file_upload_request: FileUploadRequest,
    current_user_clerk_id: str = Depends(get_current_user_clerk_id),
):
    """
    Logic Flow:
    1. Verify project exists and belongs to the current user
    2. Generate s3 key
    3. Generate upload presigned url (will expire in 1 hour)
    4. Create project document record with pending status
    5. Return presigned url
    """
    try:
        logger.info(
            "get_presigned_url_started",
            project_id=project_id,
            filename=file_upload_request.file_name,
        )
        # Verify project exists and belongs to the current user
        project_ownership_verification_result = (
            supabase.table("projects")
            .select("id")
            .eq("id", project_id)
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )

        if not project_ownership_verification_result.data:
            logger.warning("get_presigned_url_forbidden", project_id=project_id)
            raise HTTPException(
                status_code=404,
                detail="Project not found or you don't have permission to upload files to this project",
            )

        # Generate s3 key
        file_extension = (
            file_upload_request.file_name.split(".")[-1]
            if "." in file_upload_request.file_name
            else ""
        )
        unique_file_id = uuid.uuid4()
        s3_key = (
            f"projects/{project_id}/documents/{unique_file_id}.{file_extension}"
            if file_extension
            else f"projects/{project_id}/documents/{unique_file_id}"
        )

        # Generate upload presigned url (will expire in 1 hour)
        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": appConfig["s3_bucket_name"],
                "Key": s3_key,
                "ContentType": file_upload_request.file_type,
            },
            ExpiresIn=3600,  # 1 hour
        )

        if not presigned_url:
            logger.error("get_presigned_url_failed", project_id=project_id)
            raise HTTPException(
                status_code=422,
                detail="Failed to generate upload presigned url",
            )

        # Generate database record with pending status
        document_creation_result = (
            supabase.table("project_documents")
            .insert(
                {
                    "project_id": project_id,
                    "filename": file_upload_request.file_name,
                    "s3_key": s3_key,
                    "file_size": file_upload_request.file_size,
                    "file_type": file_upload_request.file_type,
                    "processing_status": ProcessingStatus.PENDING,
                    "clerk_id": current_user_clerk_id,
                }
            )
            .execute()
        )

        if not document_creation_result.data:
            logger.error("get_presigned_url_db_failed", project_id=project_id)
            raise HTTPException(
                status_code=422,
                detail="Failed to create project document - invalid data provided",
            )

        logger.info("get_presigned_url_success", project_id=project_id, s3_key=s3_key)
        return {
            "success": True,
            "message": "Upload presigned url generated successfully",
            "data": {
                "presigned_url": presigned_url,
                "s3_key": s3_key,
                "project_document": document_creation_result.data[0],
            },
        }
    except Exception as e:
        logger.error(
            "get_presigned_url_exception",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while generating upload presigned url for {project_id}: {str(e)}",
        )


@router.post("/{project_id}/files/confirm-upload-to-s3")
async def confirm_file_upload_to_s3(
    project_id: str,
    confirm_file_upload_request: dict,
    current_user_clerk_id: str = Depends(get_current_user_clerk_id),
):
    try:
        s3_key = confirm_file_upload_request["s3_key"]
        logger.info("confirm_s3_upload_started", project_id=project_id, s3_key=s3_key)
        if not s3_key:
            raise HTTPException(
                status_code=400,
                detail="S3 key is required",
            )

        # Verify file exists in database
        document_verification_result = (
            supabase.table("project_documents")
            .select("id")
            .eq("s3_key", s3_key)
            .eq("project_id", project_id)
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )

        if not document_verification_result.data:
            logger.warning("confirm_s3_upload_not_found_forbidden", s3_key=s3_key)
            raise HTTPException(
                status_code=404,
                detail="File not found or you don't have permission to confirm upload to S3 for this file",
            )

        # Update file status to "queued"
        # Not 'completed' because the file is not yet processed - RAG pipeline will process it
        document_update_result = (
            supabase.table("project_documents")
            .update(
                {
                    "processing_status": ProcessingStatus.QUEUED,
                }
            )
            .eq("s3_key", s3_key)
            .execute()
        )

        # * Start Background pre-processing of this document using Celery Task
        document_id = document_update_result.data[0]["id"]
        # * Celery Task - returns a task id - Store to track later
        task_result = perform_rag_ingestion_task.delay(document_id)
        task_id = task_result.id
        logger.info(
            "confirm_s3_upload_task_started", task_id=task_id, document_id=document_id
        )

        # Update the project document record with the task_id
        document_update_result = (
            supabase.table("project_documents")
            .update(
                {
                    "task_id": task_id,
                }
            )
            .eq("id", document_id)
            .execute()
        )
        if not document_update_result.data:
            logger.error("confirm_s3_upload_update_failed", document_id=document_id)
            raise HTTPException(
                status_code=422,
                detail="Failed to update project document record with task_id",
            )

        logger.info("confirm_s3_upload_success", document_id=document_id)
        return {
            "success": True,
            "message": "File upload to S3 confirmed successfully And Started Background Pre-Processing of this file",
            "data": {
                "file_update_result": document_update_result.data[0],
            },
        }

    except Exception as e:
        logger.error(
            "confirm_s3_upload_exception",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while confirming upload to S3 for {project_id}: {str(e)}",
        )


@router.post("/{project_id}/files/process-url")
async def process_url(
    project_id: str,
    url: UrlRequest,
    current_user_clerk_id: str = Depends(get_current_user_clerk_id),
):
    try:
        # Validate URL
        url = url.url
        logger.info("process_url_started", project_id=project_id, url=url)
        if url.startswith("http://") or url.startswith("https://"):
            url = url
        else:
            url = f"https://{url}"

        if not validate_url(url):
            raise HTTPException(
                status_code=400,
                detail="Invalid URL",
            )

        # Add website Url to database
        document_creation_result = (
            supabase.table("project_documents")
            .insert(
                {
                    "project_id": project_id,
                    "filename": url,
                    "s3_key": "",
                    "file_size": 0,
                    "file_type": "text/html",
                    "processing_status": ProcessingStatus.QUEUED,
                    "clerk_id": current_user_clerk_id,
                    "source_type": "url",
                    "source_url": url,
                }
            )
            .execute()
        )

        if not document_creation_result.data:
            logger.error("process_url_db_failed", project_id=project_id, url=url)
            raise HTTPException(
                status_code=422,
                detail="Failed to create project document with URL Record - invalid data provided",
            )

        # * Start Background pre-processing of this document using Celery Task
        document_id = document_creation_result.data[0]["id"]
        # * Celery Task - returns a task id - Store to track later
        task_result = perform_rag_ingestion_task.delay(document_id)
        task_id = task_result.id
        logger.info(
            "process_url_task_started", task_id=task_id, document_id=document_id
        )

        #  Update the project document record with the task_id
        document_update_result = (
            supabase.table("project_documents")
            .update(
                {
                    "task_id": task_id,
                }
            )
            .eq("id", document_id)
            .execute()
        )

        if not document_update_result.data:
            logger.error("process_url_update_failed", document_id=document_id)
            raise HTTPException(
                status_code=422,
                detail="Failed to update project document record with task_id",
            )

        logger.info("process_url_success", document_id=document_id)
        return {
            "success": True,
            "message": "Website URL added to database successfully And Started Background Pre-Processing of this URL",
            "data": {
                "document_creation_result": document_creation_result.data[0],
            },
        }

    except Exception as e:
        logger.error(
            "process_url_exception", project_id=project_id, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while processing urls for {project_id}: {str(e)}",
        )


@router.delete("/{project_id}/files/delete/{document_id}")
async def delete_project_document(
    project_id: str,
    document_id: str,
    current_user_clerk_id: str = Depends(get_current_user_clerk_id),
):
    try:
        logger.info(
            "delete_document_started", project_id=project_id, document_id=document_id
        )
        # Verify document exists and belongs to the current user and Take complete project document record
        document_ownership_verification_result = (
            supabase.table("project_documents")
            .select("*")
            .eq("id", document_id)
            .eq("project_id", project_id)
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )

        if not document_ownership_verification_result.data:
            raise HTTPException(
                status_code=404,
                detail="Document not found or you don't have permission to delete this document",
            )

        # Delete file from S3 (only for actual files, not for URLs)
        s3_key = document_ownership_verification_result.data[0]["s3_key"]
        if s3_key:
            s3_client.delete_object(Bucket=appConfig["s3_bucket_name"], Key=s3_key)

        # Delete document from database
        document_deletion_result = (
            supabase.table("project_documents")
            .delete()
            .eq("id", document_id)
            .eq("project_id", project_id)
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )

        if not document_deletion_result.data:
            logger.error("delete_document_failed", document_id=document_id)
            raise HTTPException(
                status_code=404,
                detail="Failed to delete document",
            )

        logger.info("delete_document_success", document_id=document_id)
        return {
            "success": True,
            "message": "Document deleted successfully",
            "data": document_deletion_result.data[0],
        }
    except Exception as e:
        logger.error(
            "delete_document_exception",
            document_id=document_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while deleting project document {document_id} for {project_id}: {str(e)}",
        )


@router.get("/{project_id}/files/{document_id}/chunks")
async def get_project_document_chunks(
    project_id: str,
    document_id: str,
    current_user_clerk_id: str = Depends(get_current_user_clerk_id),
):
    try:
        logger.info(
            "get_chunks_started", project_id=project_id, document_id=document_id
        )
        # Verify document exists and belongs to the current user and Take complete project document record
        document_ownership_verification_result = (
            supabase.table("project_documents")
            .select("*")
            .eq("id", document_id)
            .eq("project_id", project_id)
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )

        if not document_ownership_verification_result.data:
            logger.warning(
                "get_chunks_document_not_found_forbidden", document_id=document_id
            )
            raise HTTPException(
                status_code=404,
                detail="Document not found or you don't have permission to delete this document",
            )

        document_chunks_result = (
            supabase.table("document_chunks")
            .select("*")
            .eq("document_id", document_id)
            .order("chunk_index")
            .execute()
        )

        logger.info(
            "get_chunks_success",
            document_id=document_id,
            count=len(document_chunks_result.data),
        )
        return {
            "success": True,
            "message": "Project document chunks retrieved successfully",
            "data": document_chunks_result.data or [],
        }
    except Exception as e:
        logger.error(
            "get_chunks_exception", document_id=document_id, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while getting project document chunks for {document_id} for {project_id}: {str(e)}",
        )
