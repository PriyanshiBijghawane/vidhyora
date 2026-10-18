import logging
from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse, JSONResponse
from backend.models import ImproveRequest
from backend.config import CREDIT_COST_PER_GENERATION
from backend.db import get_user_by_id, save_improve_workspace
from backend.services.gemini_service import sse_event
from backend.services.agent_service import run_improve_agent

logger = logging.getLogger("backend.routes.improve")
router = APIRouter(prefix="/api", tags=["Code Improvement"])

@router.post("/improve")
async def improve_code(req: ImproveRequest):
    user = await get_user_by_id(req.userId)
    if not user:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "User not found"}
        )

    # Pro-only gate
    if user.get("plan") != "pro":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"message": "Upgrade required"}
        )

    if user.get("credits", 0) < CREDIT_COST_PER_GENERATION:
        return JSONResponse(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            content={"message": "Insufficient credits"}
        )

    async def event_generator():
        try:
            async for sse_chunk in run_improve_agent(req.userRequest, req.fileData):
                # When done event is emitted, persist to DB and update remaining credits
                if '"type": "done"' in sse_chunk or '"type":"done"' in sse_chunk:
                    try:
                        # Extract fileData from done event or updated state
                        credits_remaining = await save_improve_workspace(
                            workspace_id=req.workspaceId,
                            user_id=req.userId,
                            file_data=req.fileData.model_dump(),
                            credit_cost=CREDIT_COST_PER_GENERATION
                        )
                    except Exception as db_err:
                        logger.error(f"Error saving workspace: {db_err}")
                yield sse_chunk

        except Exception as e:
            logger.error(f"[improve] error: {e}", exc_info=True)
            yield sse_event("error", {"message": "Something went wrong."})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
