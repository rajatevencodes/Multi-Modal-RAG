from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from src.services.supabase import supabase
from src.services.clerkAuth import get_current_user_clerk_id
from src.models.index import ProjectCreate, ProjectSettings
from src.config.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["projectRoutes"])

"""
`/api/project`

List all projects: GET `/list`
Create a new project: POST `/create`
Delete a project: DELETE `/delete/{project_id}`
Get a project: GET `/{project_id}`
Get project chats: GET `/{project_id}/chats`
Get project settings: GET `/{project_id}/settings`
Update project settings: PUT `/{project_id}/settings/update`

"""


@router.get("/list")
async def get_projects(current_user_clerk_id: str = Depends(get_current_user_clerk_id)):
    try:
        logger.info("get_projects_started", user_id=current_user_clerk_id)
        projects_query_result = (
            supabase.table("projects")
            .select("*")
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )

        logger.info("get_projects_success", count=len(projects_query_result.data))
        return {
            "success": True,
            "message": "Projects retrieved successfully",
            "data": projects_query_result.data,
        }
    except Exception as e:
        logger.error("get_projects_exception", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while fetching projects: {str(e)}",
        )


@router.post("/create")
async def create_project(
    project_data: ProjectCreate,
    current_user_clerk_id: str = Depends(get_current_user_clerk_id),
):
    try:
        logger.info("create_project_started", project_name=project_data.name)
        # Insert new project into database
        project_insert_data = {
            "name": project_data.name,
            "description": project_data.description,
            "clerk_id": current_user_clerk_id,
        }

        project_creation_result = (
            supabase.table("projects").insert(project_insert_data).execute()
        )

        if not project_creation_result.data:
            logger.error("create_project_failed_db_insert")
            raise HTTPException(
                status_code=422,
                detail="Failed to create project - invalid data provided",
            )

        newly_created_project = project_creation_result.data[0]

        # Create default project settings for the new project
        project_settings_data = {
            "project_id": newly_created_project["id"],
            "embedding_model": "text-embedding-3-large",
            "rag_strategy": "basic",
            "agent_type": "agentic",
            "chunks_per_search": 10,
            "final_context_size": 5,
            "similarity_threshold": 0.3,
            "number_of_queries": 5,
            "reranking_enabled": True,
            "reranking_model": "reranker-english-v3.0",
            "vector_weight": 0.7,
            "keyword_weight": 0.3,
        }

        project_settings_creation_result = (
            supabase.table("project_settings").insert(project_settings_data).execute()
        )

        if not project_settings_creation_result.data:
            logger.error(
                "create_project_failed_settings", project_id=newly_created_project["id"]
            )
            # Rollback: Delete the project if settings creation fails
            supabase.table("projects").delete().eq(
                "id", newly_created_project["id"]
            ).execute()
            raise HTTPException(
                status_code=422,
                detail="Failed to create project settings - project creation rolled back",
            )

        newly_created_project_settings = project_settings_creation_result.data[0]

        logger.info("create_project_success", project_id=newly_created_project["id"])
        return {
            "success": True,
            "message": "Project created successfully",
            "data": {
                "project": newly_created_project,
                "settings": newly_created_project_settings,
            },
        }
    except Exception as e:
        logger.error("create_project_exception", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while creating project: {str(e)}",
        )


@router.delete("/delete/{project_id}")
async def delete_project(
    project_id: str, current_user_clerk_id: str = Depends(get_current_user_clerk_id)
):
    try:
        logger.info("delete_project_started", project_id=project_id)
        # Verify if the project exists and belongs to the current user
        project_ownership_verification_result = (
            supabase.table("projects")
            .select("id")
            .eq("id", project_id)
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )

        if not project_ownership_verification_result.data:
            logger.warning(
                "delete_project_not_found_or_forbidden", project_id=project_id
            )
            raise HTTPException(
                status_code=404,  # Not Found - project doesn't exist or doesn't belong to user
                detail="Project not found or you don't have permission to delete it",
            )

        project_to_delete = project_ownership_verification_result.data[0]

        # Delete project - CASCADE will automatically delete all related data:
        # project_settings, project_documents, document_chunks, chats, messages, etc.
        project_deletion_result = (
            supabase.table("projects")
            .delete()
            .eq("id", project_id)
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )

        if not project_deletion_result.data:
            logger.error("delete_project_failed", project_id=project_id)
            raise HTTPException(
                status_code=500,  # Internal Server Error - deletion failed unexpectedly
                detail="Failed to delete project - please try again",
            )

        successfully_deleted_project = project_deletion_result.data[0]
        logger.info("delete_project_success", project_id=project_id)

        return {
            "success": True,
            "message": "Project deleted successfully",
            "data": {"deleted_project": successfully_deleted_project},
        }
    except Exception as e:
        logger.error(
            "delete_project_exception",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while deleting project: {str(e)}",
        )


@router.get("/{project_id}")
async def get_project(
    project_id: str, current_user_clerk_id: str = Depends(get_current_user_clerk_id)
):
    try:
        logger.info("get_project_started", project_id=project_id)
        project_result = (
            supabase.table("projects")
            .select("*")
            .eq("id", project_id)
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )

        if not project_result.data:
            logger.warning("get_project_not_found_or_forbidden", project_id=project_id)
            raise HTTPException(
                status_code=404,
                detail="Project not found or you don't have permission to access it",
            )

        logger.info("get_project_success", project_id=project_id)
        return {
            "success": True,
            "message": "Project retrieved successfully",
            "data": project_result.data[0],
        }
    except Exception as e:
        logger.error(
            "get_project_exception", project_id=project_id, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while retrieving project: {str(e)}",
        )


@router.get("/{project_id}/chats")
async def get_project_chats(
    project_id: str, current_user_clerk_id: str = Depends(get_current_user_clerk_id)
):
    try:
        logger.info("get_project_chats_started", project_id=project_id)
        project_chats_result = (
            supabase.table("chats")
            .select("*")
            .eq("project_id", project_id)
            .eq("clerk_id", current_user_clerk_id)
            .order("created_at", desc=True)
            .execute()
        )

        # if not project_chats_result.data:
        #     raise HTTPException(
        #         status_code=404,
        #         detail="No chats found for project",
        #     )

        logger.info(
            "get_project_chats_success",
            project_id=project_id,
            count=len(project_chats_result.data),
        )
        return {
            "success": True,
            "message": "Project chats retrieved successfully",
            "data": project_chats_result.data,  # Not result.data[0] because we are returning all chats for the project
        }
    except Exception as e:
        logger.error(
            "get_project_chats_exception",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while retrieving project {project_id} chats: {str(e)}",
        )


@router.get("/{project_id}/settings")
async def get_project_settings(
    project_id: str, current_user_clerk_id: str = Depends(get_current_user_clerk_id)
):
    try:
        logger.info("get_project_settings_started", project_id=project_id)
        project_settings_result = (
            supabase.table("project_settings")
            .select("*")
            .eq("project_id", project_id)
            .execute()
        )

        if not project_settings_result.data:
            logger.warning("get_project_settings_not_found", project_id=project_id)
            raise HTTPException(
                status_code=404,
                detail="No settings found for project",
            )

        logger.info("get_project_settings_success", project_id=project_id)
        return {
            "success": True,
            "message": "Project settings retrieved successfully",
            "data": project_settings_result.data[0],
        }
    except Exception as e:
        logger.error(
            "get_project_settings_exception",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while retrieving project {project_id} settings: {str(e)}",
        )


@router.put("/{project_id}/settings/update")
async def update_project_settings(
    project_id: str,
    settings: ProjectSettings,
    current_user_clerk_id: str = Depends(get_current_user_clerk_id),
):
    try:
        logger.info("update_project_settings_started", project_id=project_id)
        # Verify if the project settings exist and belongs to the current user
        # First verify the project belongs to the user
        project_ownership_verification_result = (
            supabase.table("projects")
            .select("id")
            .eq("id", project_id)
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )

        if not project_ownership_verification_result.data:
            logger.warning("update_project_settings_forbidden", project_id=project_id)
            raise HTTPException(
                status_code=404,
                detail="Project not found or you don't have permission to update its settings",
            )

        # Then verify the project settings exist
        project_settings_ownership_verification_result = (
            supabase.table("project_settings")
            .select("id")
            .eq("project_id", project_id)
            .execute()
        )

        if not project_settings_ownership_verification_result.data:
            raise HTTPException(
                status_code=404,
                detail="Project settings not found for this project",
            )

        project_settings_update_data = (
            settings.model_dump()  # Pydantic modal to dictionary conversion
        )
        project_settings_update_result = (
            supabase.table("project_settings")
            .update(project_settings_update_data)
            .eq("project_id", project_id)
            .execute()
        )

        if not project_settings_update_result.data:
            logger.error("update_project_settings_failed", project_id=project_id)
            raise HTTPException(
                status_code=422, detail="Failed to update project settings"
            )

        logger.info("update_project_settings_success", project_id=project_id)
        return {
            "success": True,
            "message": "Project settings updated successfully",
            "data": project_settings_update_result.data[0],
        }
    except Exception as e:
        logger.error(
            "update_project_settings_exception",
            project_id=project_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=str(e))
