import json
import logging
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from backend.models import GenAICodeRequest
from backend.config import CREDIT_COST_PER_GENERATION
from backend.db import get_user_by_id, save_gen_ai_workspace
from backend.services.gemini_service import (
    sse_event,
    validate_dependencies,
    generate_code_stream
)

logger = logging.getLogger("backend.routes.gen_ai_code")
router = APIRouter(prefix="/api", tags=["Code Generation"])

@router.post("/gen-ai-code")
async def generate_ai_code(req: GenAICodeRequest):
    if not req.messages:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "No messages provided"}
        )

    user = await get_user_by_id(req.userId)
    if not user:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "User not found"}
        )

    if user.get("credits", 0) < CREDIT_COST_PER_GENERATION:
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={"message": "Insufficient credits"}
        )

    async def event_generator():
        accumulated_json = ""
        try:
            async for event in generate_code_stream(req.messages, req.fileData):
                ev_type = event.get("type")
                if ev_type == "thought":
                    yield sse_event("status", {"message": event["label"]})
                elif ev_type == "content":
                    accumulated_json += event["chunk"]
                elif ev_type == "error":
                    yield sse_event("error", {"message": event["message"]})
                    return

            # Parse JSON
            try:
                parsed = json.loads(accumulated_json)
            except Exception:
                yield sse_event("error", {"message": "AI returned invalid JSON. Please try again."})
                return

            assistant_msg = parsed.get("assistantMessage", "")
            ai_title = parsed.get("title")
            raw_files = parsed.get("files")
            raw_dependencies = parsed.get("dependencies", {})

            if not raw_files or not isinstance(raw_files, dict):
                yield sse_event("error", {"message": "AI response missing files. Please try again."})
                return

            # Sanitize files and dependencies to remove import.meta and forbidden auth packages
            from backend.services.sanitizer import sanitize_code_and_files
            files, dependencies = sanitize_code_and_files(raw_files, raw_dependencies)

            # Validate packages
            yield sse_event("status", {"message": "Validating packages…"})
            validated_deps = await validate_dependencies(dependencies)

            new_file_data = {
                "files": files,
                "dependencies": validated_deps,
                "title": ai_title
            }

            # Save to Database & deduct credits
            yield sse_event("status", {"message": "Saving…"})

            updated_messages = [
                m.model_dump() for m in req.messages
            ] + [{"role": "assistant", "content": assistant_msg}]

            last_user_content = req.messages[-1].content if req.messages else "New Project"
            project_title = ai_title or last_user_content[:80]

            workspace_id, credits_remaining = await save_gen_ai_workspace(
                workspace_id=req.workspaceId,
                user_id=req.userId,
                title=project_title,
                messages=updated_messages,
                file_data=new_file_data,
                credit_cost=CREDIT_COST_PER_GENERATION
            )

            # Emit final done event
            yield sse_event("done", {
                "workspaceId": workspace_id,
                "assistantMessage": assistant_msg,
                "fileData": new_file_data,
                "creditsRemaining": credits_remaining
            })

        except Exception as e:
            logger.error(f"[gen-ai-code] error: {e}", exc_info=True)
            yield sse_event("error", {"message": "Something went wrong. Please try again."})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
