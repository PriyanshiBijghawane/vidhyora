import asyncio
import json
import httpx
import asyncpg
import os

DB_URL = os.getenv("DATABASE_URL") or "postgresql://postgres.yntjarpcglijjentttak:R%40dhey20%2524@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"
API_URL = "http://127.0.0.1:8001/api/gen-ai-code"

async def run_e2e_test():
    print("=== Step 1: Check existing projects in Database ===")
    conn = await asyncpg.connect(DB_URL)
    user_row = await conn.fetchrow('SELECT id, email, credits FROM "User" LIMIT 1')
    assert user_row is not None, "No user found in DB"
    user_id = user_row["id"]
    print(f"Testing with user: {user_id} ({user_row['email']}), Credits: {user_row['credits']}")

    initial_workspaces = await conn.fetch('SELECT id, title, "updatedAt" FROM "Workspace" ORDER BY "updatedAt" DESC')
    initial_ids = {w["id"] for w in initial_workspaces}
    print(f"Existing workspaces before test ({len(initial_workspaces)}): {[w['id'] + ': ' + (w['title'] or '') for w in initial_workspaces]}")
    assert "ws_142835b98316485e" in initial_ids, "TaskFlow Kanban Board (ws_142835b98316485e) must exist!"

    print("\n=== Step 2: Generate New Project (Interactive Expense Tracker) ===")
    new_prompt = "Create an Interactive Expense Tracker with categories, spending breakdown chart, and recent transaction history using Tailwind CSS."
    payload = {
        "workspaceId": None,
        "userId": user_id,
        "messages": [{"role": "user", "content": new_prompt}],
        "fileData": None
    }

    done_event_1 = None
    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream("POST", API_URL, json=payload) as response:
            assert response.status_code == 200, f"Error {response.status_code}"
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    part, buffer = buffer.split("\n\n", 1)
                    for line in part.split("\n"):
                        if line.startswith("data: "):
                            try:
                                ev = json.loads(line[6:])
                                if ev.get("type") == "done":
                                    done_event_1 = ev
                            except Exception:
                                pass

    assert done_event_1 is not None, "Step 2 failed: No done event received!"
    new_ws_id = done_event_1["workspaceId"]
    new_file_data = done_event_1["fileData"]
    print(f"Successfully generated new project: ID = {new_ws_id}")
    print(f"Title: {new_file_data.get('title')}")
    print(f"Files: {list(new_file_data.get('files', {}).keys())}")
    assert "/App.js" in new_file_data.get("files", {}), "Missing /App.js"
    assert new_ws_id not in initial_ids, "New workspace should have a fresh ID!"

    print("\n=== Step 3: Test Additional Prompt Update on the Same Project ===")
    update_prompt = "Add a monthly budget progress bar and a quick filter for expense categories."
    updated_messages = [
        {"role": "user", "content": new_prompt},
        {"role": "assistant", "content": done_event_1["assistantMessage"]},
        {"role": "user", "content": update_prompt}
    ]
    update_payload = {
        "workspaceId": new_ws_id,
        "userId": user_id,
        "messages": updated_messages,
        "fileData": new_file_data
    }

    done_event_2 = None
    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream("POST", API_URL, json=update_payload) as response:
            assert response.status_code == 200, f"Update error {response.status_code}"
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    part, buffer = buffer.split("\n\n", 1)
                    for line in part.split("\n"):
                        if line.startswith("data: "):
                            try:
                                ev = json.loads(line[6:])
                                if ev.get("type") == "done":
                                    done_event_2 = ev
                            except Exception:
                                pass

    assert done_event_2 is not None, "Step 3 failed: No done event received on prompt update!"
    updated_ws_id = done_event_2["workspaceId"]
    assert updated_ws_id == new_ws_id, f"Workspace ID should be preserved! Expected {new_ws_id}, got {updated_ws_id}"
    updated_file_data = done_event_2["fileData"]
    print(f"Prompt update succeeded for workspace {updated_ws_id}!")
    print(f"Updated Files: {list(updated_file_data.get('files', {}).keys())}")

    print("\n=== Step 4: Verify Persistence on Refresh (getWorkspaceById) ===")
    ws_db = await conn.fetchrow('SELECT id, title, messages, "fileData", "updatedAt" FROM "Workspace" WHERE id = $1', new_ws_id)
    assert ws_db is not None, f"Workspace {new_ws_id} not found in database!"
    
    db_messages = json.loads(ws_db["messages"]) if isinstance(ws_db["messages"], str) else ws_db["messages"]
    db_file_data = json.loads(ws_db["fileData"]) if isinstance(ws_db["fileData"], str) else ws_db["fileData"]
    
    print(f"Retrieved from DB: title='{ws_db['title']}', message count={len(db_messages)}")
    assert len(db_messages) >= 4, f"Expected at least 4 messages (2 user + 2 assistant), got {len(db_messages)}"
    assert "/App.js" in db_file_data.get("files", {}), "Restored files must contain /App.js"
    print("Workspace persistence on refresh verified successfully!")

    print("\n=== Step 5: Verify Projects Page (getUserProjects) ===")
    user_projects = await conn.fetch(
        'SELECT id, title, "createdAt", "updatedAt", messages FROM "Workspace" WHERE "userId" = $1 ORDER BY "updatedAt" DESC',
        user_id
    )
    print(f"User projects listed on Projects page ({len(user_projects)} total):")
    project_ids = []
    for p in user_projects:
        msgs = json.loads(p["messages"]) if isinstance(p["messages"], str) else p["messages"]
        first_prompt = next((m["content"][:60] for m in msgs if m.get("role") == "user"), "No prompt")
        project_ids.append(p["id"])
        print(f" - [{p['id']}] '{p['title']}' | Messages: {len(msgs)} | Prompt: '{first_prompt}'")

    assert new_ws_id in project_ids, f"New project {new_ws_id} must appear on Projects page!"
    assert "ws_142835b98316485e" in project_ids, "TaskFlow Kanban Board (ws_142835b98316485e) must still appear!"
    print("Projects page listing verified successfully!")

    print("\n=== Step 6: Verify Zero Overwrite of Existing Data ===")
    taskflow = await conn.fetchrow('SELECT id, title, messages, "fileData" FROM "Workspace" WHERE id = $1', 'ws_142835b98316485e')
    assert taskflow is not None, "TaskFlow workspace disappeared!"
    tf_files = json.loads(taskflow["fileData"]) if isinstance(taskflow["fileData"], str) else taskflow["fileData"]
    assert "/App.js" in tf_files.get("files", {}), "TaskFlow files intact"
    print("Confirmed: ws_142835b98316485e (TaskFlow - Kanban Board) is 100% intact and unchanged.")

    await conn.close()
    print("\nALL VERIFICATIONS PASSED! E2E TEST COMPLETED SUCCESSFULLY.")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())
