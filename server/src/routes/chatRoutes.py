from fastapi import APIRouter, HTTPException, Depends
from src.agents.supervisor_agent.agent import create_supervisor_agent
from src.agents.simple_agent.agent import create_simple_rag_agent
from src.services.supabase import supabase
from src.services.clerkAuth import get_current_user_clerk_id
from src.models.index import ChatCreate, MessageCreate, MessageRole
from src.rag.retrieval.utils import get_project_settings, get_chat_history
from src.config.logging import get_logger, set_project_id, set_user_id
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

logger = get_logger(__name__)

router = APIRouter(tags=["chatRoutes"])

"""
`/api/chat`

Create a new chat: POST `/create`
Delete a chat: DELETE `/delete/{chat_id}`
Get a specific chat: `/{chat_id}`
Create a new message for specific project and specific chat: POST `/{project_id}/chats/{chat_id}/messages/create`
Stream a message for specific project and specific chat: POST `/{project_id}/chats/{chat_id}/messages/stream`
"""


@router.post("/create")
async def create_chat(
    chat: ChatCreate, current_user_clerk_id: str = Depends(get_current_user_clerk_id)
):
    try:
        logger.info("create_chat_started", project_id=chat.project_id)
        chat_insert_data = {
            "title": chat.title,
            "project_id": chat.project_id,
            "clerk_id": current_user_clerk_id,
        }
        chat_creation_result = (
            supabase.table("chats").insert(chat_insert_data).execute()
        )

        if not chat_creation_result.data:
            logger.error("create_chat_failed_supabase", project_id=chat.project_id)
            raise HTTPException(status_code=422, detail="Failed to create chat")

        logger.info("create_chat_success", chat_id=chat_creation_result.data[0]["id"])
        return {
            "success": True,
            "message": "Chat created successfully",
            "data": chat_creation_result.data[0],
        }

    except Exception as e:
        logger.error("create_chat_exception", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while creating chat: {str(e)}",
        )


@router.delete("/delete/{chat_id}")
async def delete_chat(
    chat_id: str, current_user_clerk_id: str = Depends(get_current_user_clerk_id)
):
    try:
        logger.info("delete_chat_started", chat_id=chat_id)
        chat_deletion_result = (
            supabase.table("chats")
            .delete()
            .eq("id", chat_id)
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )
        if not chat_deletion_result.data:
            logger.warning("delete_chat_not_found", chat_id=chat_id)
            raise HTTPException(status_code=404, detail="Chat not found")

        logger.info("delete_chat_success", chat_id=chat_id)
        return {
            "success": True,
            "message": "Chat deleted successfully",
            "data": chat_deletion_result.data[0],
        }
    except Exception as e:
        logger.error(
            "delete_chat_exception", chat_id=chat_id, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while deleting chat {chat_id}: {str(e)}",
        )


@router.get("/{chat_id}")
async def get_chat(
    chat_id: str, current_user_clerk_id: str = Depends(get_current_user_clerk_id)
):
    try:
        logger.info("get_chat_started", chat_id=chat_id)
        # Verify if the chat exists and belongs to the current user
        # Selecting '*' to embeded the messages in the chat object.
        chat_ownership_verification_result = (
            supabase.table("chats")
            .select("*")
            .eq("id", chat_id)
            .eq("clerk_id", current_user_clerk_id)
            .execute()
        )

        if not chat_ownership_verification_result.data:
            logger.warning("get_chat_not_found_or_forbidden", chat_id=chat_id)
            raise HTTPException(
                status_code=404,
                detail="Chat not found or you don't have permission to access it",
            )

        chat_result = chat_ownership_verification_result.data[0]

        messages_result = (
            supabase.table("messages").select("*").eq("chat_id", chat_id).execute()
        )
        chat_result["messages"] = messages_result.data

        logger.info("get_chat_success", chat_id=chat_id)
        return {
            "success": True,
            "message": "Chat retrieved successfully",
            "data": chat_result,
        }

    except Exception as e:
        logger.error("get_chat_exception", chat_id=chat_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while getting chat {chat_id}: {str(e)}",
        )


@router.post("/{project_id}/chats/{chat_id}/messages/create")
async def create_message(
    project_id: str,
    chat_id: str,
    message: MessageCreate,
    current_user_clerk_id: str = Depends(get_current_user_clerk_id),
):
    """
    Step 1 : Insert the message into the database.
    Step 2 : Get Project Settings from the database - Retrieval will be performed by the agent.(Simple or Agentic)
             Based on the agent_type, Retrieval will be performed by the agent.
    Step 3 : Get Chat History and perform Retrieval
    Step 4 : Invoke the agent_type(Simple or Agentic) for generation (Retrieved Context + User Message)
    Step 5 : Insert the AI Response into the database.
    """
    try:
        logger.info("create_message_started", chat_id=chat_id, project_id=project_id)
        # Step 1 : Insert the message into the database.
        message = message.content
        message_insert_data = {
            "content": message,
            "chat_id": chat_id,
            "clerk_id": current_user_clerk_id,
            "role": MessageRole.USER.value,
        }
        message_creation_result = (
            supabase.table("messages").insert(message_insert_data).execute()
        )

        if not message_creation_result.data:
            logger.error("create_message_failed_user_msg", chat_id=chat_id)
            raise HTTPException(status_code=422, detail="Failed to create message")

        # Step 2 : Get Project Settings from the database - Retrieval will be performed by the agent.
        # Based on the agent_type, Retrieval will be performed by the agent.
        try:
            project_settings = get_project_settings(project_id)
            agent_type = project_settings.get("agent_type", "simple")
        except Exception as e:
            agent_type = "simple"

        # Step 3: Get chat history
        chat_history = get_chat_history(chat_id)

        # Step 4: Create the appropriate agent
        if agent_type == "simple":
            agent = create_simple_rag_agent(project_id, chat_history=chat_history)

        if agent_type == "agentic":
            agent = create_supervisor_agent(project_id, chat_history=chat_history)

        # Step 5: Insert the AI Response into the database.
        result = agent.invoke({"messages": [{"role": "user", "content": message}]})
        final_response = result["messages"][-1].content
        citations = result.get("citations", [])

        ai_response_insert_data = {
            "content": final_response,
            "chat_id": chat_id,
            "clerk_id": current_user_clerk_id,
            "role": MessageRole.ASSISTANT.value,
            "citations": citations,
        }
        ai_response_creation_result = (
            supabase.table("messages").insert(ai_response_insert_data).execute()
        )
        if not ai_response_creation_result.data:
            logger.error("create_message_failed_ai_resp", chat_id=chat_id)
            raise HTTPException(status_code=422, detail="Failed to create AI response")

        logger.info("create_message_success", chat_id=chat_id)
        return {
            "success": True,
            "message": "Message created successfully",
            "data": {
                "userMessage": message_creation_result.data[0],
                "aiResponse": ai_response_creation_result.data[0],
            },
        }

    except Exception as e:
        logger.error(
            "create_message_exception", chat_id=chat_id, error=str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred while creating message: {str(e)}",
        )


@router.post("/{project_id}/chats/{chat_id}/messages/stream")
async def stream_message(
    project_id: str,
    chat_id: str,
    message: MessageCreate,
    current_user_clerk_id: str = Depends(get_current_user_clerk_id),
):
    """
    Step 1 : Insert the message into the database.
    Step 2 : Get Project Settings from the database - Retrieval will be performed by the agent.(Simple or Agentic)
             Based on the agent_type, Retrieval will be performed by the agent.
    Step 3 : Get Chat History and perform Retrieval
    Step 4 : Invoke the agent_type(Simple or Agentic) for generation (Retrieved Context + User Message)
    Step 5 : Stream the Response
    Step 6 : Insert the AI Response into the database.
    Step 7 : Send done event
    """
    set_project_id(project_id)
    set_user_id(current_user_clerk_id)

    async def event_generator():
        try:
            logger.info("sending_message", chat_id=chat_id)

            # Step 1: Insert user message into database
            message_content = message.content
            message_insert_data = {
                "content": message_content,
                "chat_id": chat_id,
                "clerk_id": current_user_clerk_id,
                "role": MessageRole.USER.value,
            }
            message_creation_result = (
                supabase.table("messages").insert(message_insert_data).execute()
            )
            if not message_creation_result.data:
                logger.error(
                    "message_creation_failed",
                    chat_id=chat_id,
                    reason="no_data_returned",
                )
                yield f"event: error\ndata: {json.dumps({'message': 'Failed to create message'})}\n\n"
                return

            user_message_data = message_creation_result.data[0]
            current_message_id = user_message_data["id"]
            logger.info(
                "user_message_created", message_id=current_message_id, chat_id=chat_id
            )  # Added: Success log

            #  Step 2 : Get Project Settings from the database - Retrieval will be performed by the agent.(Simple or Agentic)
            #   Based on the agent_type, Retrieval will be performed by the agent.

            try:
                project_settings = get_project_settings(project_id)
                agent_type = project_settings.get("agent_type", "simple")
            except Exception as e:
                logger.warning(
                    "settings_retrieval_failed_defaulting_to_simple", error=str(e)
                )
                agent_type = "simple"

            logger.info("agent_type_determined", agent_type=agent_type)

            # Step 3: Get chat history
            chat_history = get_chat_history(
                chat_id, exclude_message_id=current_message_id
            )

            # Step 4: Create the appropriate agent
            if agent_type == "simple":
                agent = create_simple_rag_agent(project_id, chat_history=chat_history)
            if agent_type == "agentic":
                agent = create_supervisor_agent(project_id, chat_history=chat_history)

            # Step 5: Stream the agent response
            full_response = ""
            citations = []

            # Track state to know when we're in the final response
            passed_guardrail = False
            tool_called = False
            is_final_response = False
            async for event in agent.astream_events(
                {"messages": [{"role": "user", "content": message_content}]},
                version="v2",
            ):
                kind = event["event"]
                tags = event.get("tags", [])
                name = event.get("name", "")

                # Detect guardrail completion
                if kind == "on_chain_end" and name == "guardrail":
                    # Check if guardrail rejected the input
                    output = event.get("data", {}).get("output", {})
                    if output.get("guardrail_passed") == False:
                        # Stream the rejection message
                        messages = output.get("messages", [])
                        if messages:
                            rejection_content = (
                                messages[0].content
                                if hasattr(messages[0], "content")
                                else str(messages[0])
                            )
                            full_response = rejection_content
                            yield f"event: token\ndata: {json.dumps({'content': rejection_content})}\n\n"
                    else:
                        passed_guardrail = True
                        yield f"event: status\ndata: {json.dumps({'status': 'Thinking...'})}\n\n"

                # Status updates for tool calls
                elif kind == "on_tool_start":
                    tool_called = True
                    tool_name = name
                    if tool_name == "rag_search":
                        yield f"event: status\ndata: {json.dumps({'status': 'Searching documents...'})}\n\n"
                    elif tool_name == "search_web":
                        yield f"event: status\ndata: {json.dumps({'status': 'Searching the web...'})}\n\n"

                # Detect when tool ends - next model call will be the final response
                elif kind == "on_tool_end":
                    is_final_response = True
                    yield f"event: status\ndata: {json.dumps({'status': 'Generating response...'})}\n\n"

                # Stream tokens from the model
                elif kind == "on_chat_model_stream":
                    # Stream if:
                    # 1. Guardrail passed AND
                    # 2. Either tool finished OR no tool was called yet
                    # Relaxed check for seq:step:1 to ensure we capture tokens
                    should_stream = passed_guardrail and (
                        is_final_response or not tool_called
                    )

                    if should_stream:
                        chunk = event["data"].get("chunk")
                        if chunk:
                            # Handle both Pydantic objects (AIMessageChunk) and dicts
                            content = (
                                chunk.content
                                if hasattr(chunk, "content")
                                else chunk.get("content", "")
                            )
                            if content:
                                full_response += content
                                yield f"event: token\ndata: {json.dumps({'content': content})}\n\n"

                # Capture citations from the final state
                elif kind == "on_chain_end" and name == "LangGraph":
                    # This is the outermost LangGraph ending
                    output = event.get("data", {}).get("output", {})
                    if isinstance(output, dict) and "citations" in output:
                        citations = output["citations"]

            logger.info(
                "agent_invocation_completed",
                chat_id=chat_id,
                response_length=len(full_response),
                citations_count=len(citations),
            )  # Added: Completion log

            # Step 6: Insert AI response into database
            if not full_response:
                logger.warning("empty_response_generated", chat_id=chat_id)
                full_response = (
                    "I apologize, but I couldn't generate a response. Please try again."
                )

            ai_response_insert_data = {
                "content": full_response,
                "chat_id": chat_id,
                "clerk_id": current_user_clerk_id,
                "role": MessageRole.ASSISTANT.value,
                "citations": citations,
            }

            logger.info(
                "inserting_ai_response",
                chat_id=chat_id,
                data_keys=list(ai_response_insert_data.keys()),
            )

            ai_response_creation_result = (
                supabase.table("messages").insert(ai_response_insert_data).execute()
            )

            if not ai_response_creation_result.data:
                logger.error(
                    "ai_response_creation_failed",
                    chat_id=chat_id,
                    reason="no_data_returned",
                )  # Added: Error log
                yield f"event: error\ndata: {json.dumps({'message': 'Failed to save AI response'})}\n\n"
                return

            ai_message_data = ai_response_creation_result.data[0]
            logger.info(
                "message_sent_successfully",
                chat_id=chat_id,
                ai_message_id=ai_message_data["id"],
            )  # Added: Success log

            # Step 7: Send done event
            yield f"event: done\ndata: {json.dumps({'userMessage': user_message_data, 'aiMessage': ai_message_data})}\n\n"

        except Exception as e:
            logger.error(
                "send_message_error", chat_id=chat_id, error=str(e), exc_info=True
            )  # Added: Exception log
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
