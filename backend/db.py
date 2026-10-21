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
            clean_url = DATABASE_URL
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
                # Auto-create user if not found so generation can proceed smoothly
                row = await conn.fetchrow(
                    'INSERT INTO "User" ("id", "clerkId", "name", "email", "credits", "plan", "createdAt", "updatedAt") '
                    'VALUES ($1, $1, $2, $3, 100, $4, NOW(), NOW()) '
                    'ON CONFLICT ("clerkId") DO UPDATE SET "updatedAt" = NOW() RETURNING "id", "credits", "plan"',
                    user_id, f"User {user_id[:8]}", f"{user_id}@vidhyora.app", "pro"
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
                    # 1. Resolve user record and deduct credits
                    user_row = await conn.fetchrow(
                        'SELECT "id", "credits" FROM "User" WHERE "id" = $1 OR "clerkId" = $1',
                        user_id
                    )
                    if not user_row:
                        user_row = await conn.fetchrow(
                            'INSERT INTO "User" ("id", "clerkId", "name", "email", "credits", "plan", "createdAt", "updatedAt") '
                            'VALUES ($1, $1, $2, $3, 100, $4, NOW(), NOW()) '
                            'ON CONFLICT ("clerkId") DO UPDATE SET "updatedAt" = NOW() RETURNING "id", "credits"',
                            user_id, f"User {user_id[:8]}", f"{user_id}@vidhyora.app", "pro"
                        )
                    real_user_id = user_row["id"] if user_row else user_id

                    # Deduct credit
                    credit_update = await conn.fetchrow(
                        'UPDATE "User" SET "credits" = GREATEST(0, "credits" - $1) WHERE "id" = $2 RETURNING "credits"',
                        credit_cost, real_user_id
                    )
                    credits_remaining = credit_update["credits"] if credit_update else 99

                    # 2. Check if workspace exists
                    existing_ws = None
                    if workspace_id:
                        existing_ws = await conn.fetchrow(
                            'SELECT "id", "title" FROM "Workspace" WHERE "id" = $1',
                            workspace_id
                        )

                    if existing_ws:
                        # Existing project: update messages, fileData, and update title if previous was generic
                        final_title = title if (title and existing_ws["title"] in (None, "New Project", "Untitled project")) else (existing_ws["title"] or title or "New Project")
                        await conn.execute(
                            'UPDATE "Workspace" SET "messages" = $1::jsonb, "fileData" = $2::jsonb, "title" = $3, "updatedAt" = NOW() WHERE "id" = $4',
                            messages_json, file_data_json, final_title, workspace_id
                        )
                        final_workspace_id = workspace_id
                    else:
                        # New project or passed id not in DB
                        final_workspace_id = workspace_id or f"ws_{uuid.uuid4().hex[:16]}"
                        final_title = title or "New Project"
                        await conn.execute(
                            'INSERT INTO "Workspace" ("id", "userId", "title", "messages", "fileData", "createdAt", "updatedAt") '
                            'VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, NOW(), NOW())',
                            final_workspace_id, real_user_id, final_title, messages_json, file_data_json
                        )
                    return final_workspace_id, credits_remaining
        except Exception as e:
            logger.error(f"Database error in save_gen_ai_workspace: {e}", exc_info=True)

    # Standalone mock fallback
    final_ws_id = workspace_id or f"ws_{uuid.uuid4().hex[:16]}"
    return final_ws_id, 99

async def save_improve_workspace(
    workspace_id: str,
    user_id: str,
    file_data: dict,
    messages: Optional[list] = None,
    credit_cost: int = 1
) -> int:
    pool = await get_db_pool()
    file_data_json = json.dumps(file_data)
    messages_json = json.dumps(messages) if messages is not None else None

    if pool:
        try:
            async with pool.acquire() as conn:
                async with conn.transaction():
                    user_row = await conn.fetchrow(
                        'UPDATE "User" SET "credits" = GREATEST(0, "credits" - $1) WHERE "id" = $2 OR "clerkId" = $2 RETURNING "credits"',
                        credit_cost, user_id
                    )
                    credits_remaining = user_row["credits"] if user_row else 99

                    if messages_json is not None:
                        await conn.execute(
                            'UPDATE "Workspace" SET "fileData" = $1::jsonb, "messages" = $2::jsonb, "updatedAt" = NOW() WHERE "id" = $3',
                            file_data_json, messages_json, workspace_id
                        )
                    else:
                        await conn.execute(
                            'UPDATE "Workspace" SET "fileData" = $1::jsonb, "updatedAt" = NOW() WHERE "id" = $2',
                            file_data_json, workspace_id
                        )
                    return credits_remaining
        except Exception as e:
            logger.error(f"Database error in save_improve_workspace: {e}", exc_info=True)

    return 99
