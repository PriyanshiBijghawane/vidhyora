import json
import uuid
import logging
from typing import Optional, Dict, Any, Tuple
from backend.config import DATABASE_URL

logger = logging.getLogger("backend.db")

_pool = None

async def get_db_pool():
    global _pool
    if _pool is None and DATABASE_URL:
        try:
            import asyncpg
            # Clean postgres URL for asyncpg if needed
            clean_url = DATABASE_URL
            if clean_url.startswith("postgresql://") or clean_url.startswith("postgres://"):
                _pool = await asyncpg.create_pool(dsn=clean_url, min_size=1, max_size=10)
        except Exception as e:
            logger.warning(f"Could not initialize asyncpg connection pool: {e}")
            _pool = None
    return _pool

async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    pool = await get_db_pool()
    if pool:
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    'SELECT "id", "credits", "plan" FROM "User" WHERE "id" = $1 OR "clerkId" = $1',
                    user_id
                )
                if row:
                    return dict(row)
        except Exception as e:
            logger.warning(f"Error querying user {user_id}: {e}")
    # Fallback default user structure for standalone/mock usage
    return {"id": user_id, "credits": 100, "plan": "pro"}

async def save_gen_ai_workspace(
    workspace_id: Optional[str],
    user_id: str,
    title: Optional[str],
    messages: list,
    file_data: dict,
    credit_cost: int = 1
) -> Tuple[str, int]:
    pool = await get_db_pool()
    messages_json = json.dumps(messages)
    file_data_json = json.dumps(file_data)
    
    if pool:
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    # Update user credits
                    user_row = await conn.fetchrow(
                        'UPDATE "User" SET "credits" = "credits" - $1 WHERE "id" = $2 OR "clerkId" = $2 RETURNING "credits"',
                        credit_cost, user_id
                    )
                    credits_remaining = user_row["credits"] if user_row else 99

                    if workspace_id:
                        await conn.execute(
                            'UPDATE "Workspace" SET "messages" = $1::jsonb, "fileData" = $2::jsonb, "updatedAt" = NOW() WHERE "id" = $3 AND "userId" = $4',
                            messages_json, file_data_json, workspace_id, user_id
                        )
                        final_workspace_id = workspace_id
                    else:
                        final_workspace_id = f"ws_{uuid.uuid4().hex[:16]}"
                        final_title = title or "New Project"
                        await conn.execute(
                            'INSERT INTO "Workspace" ("id", "userId", "title", "messages", "fileData", "createdAt", "updatedAt") VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, NOW(), NOW())',
                            final_workspace_id, user_id, final_title, messages_json, file_data_json
                        )
                    return final_workspace_id, credits_remaining
        except Exception as e:
            logger.warning(f"Database error in save_gen_ai_workspace: {e}")

    # Standalone mock fallback
    final_ws_id = workspace_id or f"ws_{uuid.uuid4().hex[:16]}"
    return final_ws_id, 99

async def save_improve_workspace(
    workspace_id: str,
    user_id: str,
    file_data: dict,
    credit_cost: int = 1
) -> int:
    pool = await get_db_pool()
    file_data_json = json.dumps(file_data)

    if pool:
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    user_row = await conn.fetchrow(
                        'UPDATE "User" SET "credits" = "credits" - $1 WHERE "id" = $2 OR "clerkId" = $2 RETURNING "credits"',
                        credit_cost, user_id
                    )
                    credits_remaining = user_row["credits"] if user_row else 99

                    await conn.execute(
                        'UPDATE "Workspace" SET "fileData" = $1::jsonb, "updatedAt" = NOW() WHERE "id" = $2 AND "userId" = $3',
                        file_data_json, workspace_id, user_id
                    )
                    return credits_remaining
        except Exception as e:
            logger.warning(f"Database error in save_improve_workspace: {e}")

    return 99
