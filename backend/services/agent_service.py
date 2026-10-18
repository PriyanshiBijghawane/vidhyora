import json
import logging
from typing import Dict, Any, AsyncGenerator
import httpx
from backend.config import GEMINI_API_KEY
from backend.models import FileData
from backend.services.gemini_service import sse_event

logger = logging.getLogger("backend.agent_service")

AGENT_SYSTEM_PROMPT = """You are an expert React developer improving a live browser preview app.

The app uses React (functional components), Tailwind CSS for styling, and runs in Sandpack.
You CANNOT use TypeScript, CSS modules, or real npm install — only what's already available.
Available packages: react, react-dom, tailwindcss (CDN), lucide-react, recharts, react-router-dom, framer-motion, date-fns, zod, react-hook-form.

WORKFLOW:
1. Understand what the user wants improved.
2. Identify which files need to change.
3. Call update_file for each file that needs changes (always include the COMPLETE file, not just the diff).
4. Once all files are updated, call done_improving with a short summary.

RULES:
- Always write complete file contents — never partial snippets.
- Keep all existing functionality unless asked to remove it.
- The entry point is always /App.js with a default export.
- All imports must reference files you've updated or packages in the available list above.
- NEVER use `import.meta` or `import.meta.env` anywhere in code (causes 'Cannot use import.meta outside a module' error in Sandpack).
- Do NOT import `@clerk/clerk-react`, `@clerk/nextjs`, `@supabase/supabase-js`, or `firebase`. Mock/simulate user auth state (profile modal/page, settings modal, login/logout toggle) cleanly using React state (`useState`/`useContext`) so the Sandpack browser preview runs error-free."""

TOOL_DECLARATIONS = [
    {
        "name": "update_file",
        "description": "Update or rewrite a file in the React sandbox. Call once per file you need to change.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {
                    "type": "STRING",
                    "description": "File path exactly as it appears, e.g. /App.js"
                },
                "code": {
                    "type": "STRING",
                    "description": "Complete new contents of the file"
                },
                "reason": {
                    "type": "STRING",
                    "description": "One sentence explaining what you changed and why"
                }
            },
            "required": ["path", "code", "reason"]
        }
    },
    {
        "name": "done_improving",
        "description": "Call this when you have finished making all improvements.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "summary": {
                    "type": "STRING",
                    "description": "A short friendly summary of all the improvements you made (1-3 sentences)"
                }
            },
            "required": ["summary"]
        }
    }
]

async def run_improve_agent(
    user_request: str,
    file_data: FileData
) -> AsyncGenerator[str, None]:
    """
    Executes the multi-turn improve agent and yields SSE strings directly.
    """
    patched_files = dict(file_data.files)
    final_summary = ""

    # Serialize files as context
    file_context_parts = []
    for path, f_obj in file_data.files.items():
        code = f_obj.get("code", "") if isinstance(f_obj, dict) else getattr(f_obj, "code", "")
        file_context_parts.append(f"// {path}\n{code}")
    file_context = "\n\n---\n\n".join(file_context_parts)

    full_system_prompt = f"{AGENT_SYSTEM_PROMPT}\n\nHere are the current files:\n\n{file_context}"

    yield sse_event("status", {"message": "Cline agent starting…"})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    contents = [
        {"role": "user", "parts": [{"text": user_request}]}
    ]

    max_turns = 8
    turn = 0

    async with httpx.AsyncClient(timeout=120.0) as client:
        while turn < max_turns:
            turn += 1

            payload = {
                "contents": contents,
                "systemInstruction": {"parts": [{"text": full_system_prompt}]},
                "tools": [{"functionDeclarations": TOOL_DECLARATIONS}],
                "generationConfig": {"temperature": 0.7}
            }

            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                yield sse_event("error", {"message": f"Agent error: HTTP {resp.status_code}"})
                return

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                yield sse_event("error", {"message": "No response from AI agent"})
                return

            candidate = candidates[0]
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            # Check if text was emitted
            text_parts = [p.get("text") for p in parts if p.get("text")]
            if text_parts:
                combined_text = "\n".join(text_parts)
                yield sse_event("thinking", {"text": combined_text})

            # Check function calls
            function_calls = [p.get("functionCall") for p in parts if p.get("functionCall")]
            if not function_calls:
                # Agent concluded without tool call
                final_summary = "".join(text_parts)
                break

            # Add model response to conversation history
            contents.append(content)

            # Process all function calls and generate function responses
            function_responses = []
            is_done = False

            for call in function_calls:
                fn_name = call.get("name")
                args = call.get("args", {})

                if fn_name == "update_file":
                    f_path = args.get("path", "/App.js")
                    f_code = args.get("code", "")
                    f_reason = args.get("reason", "Updated file")

                    from backend.services.sanitizer import sanitize_code_and_files
                    cleaned_patch, _ = sanitize_code_and_files({f_path: {"code": f_code}}, {})
                    f_code = cleaned_patch[f_path]["code"]

                    patched_files[f_path] = {"code": f_code}
                    yield sse_event("thinking", {"text": f"\n\nUpdating `{f_path}`…"})
                    yield sse_event("file_patch", {"path": f_path, "code": f_code, "reason": f_reason})

                    function_responses.append({
                        "functionResponse": {
                            "name": fn_name,
                            "response": {"output": f"Updated {f_path}: {f_reason}"}
                        }
                    })

                elif fn_name == "done_improving":
                    final_summary = args.get("summary", "Finished making improvements.")
                    yield sse_event("thinking", {"text": "\n\nFinalizing improvements…"})
                    function_responses.append({
                        "functionResponse": {
                            "name": fn_name,
                            "response": {"output": "Done."}
                        }
                    })
                    is_done = True

            contents.append({"role": "user", "parts": function_responses})

            if is_done:
                break

    from backend.services.sanitizer import sanitize_code_and_files
    cleaned_files, cleaned_deps = sanitize_code_and_files(patched_files, file_data.dependencies)

    # Construct and yield completed payload
    new_file_data = {
        "files": cleaned_files,
        "dependencies": cleaned_deps,
        "title": file_data.title
    }

    yield sse_event("done", {
        "fileData": new_file_data,
        "summary": final_summary or "Improvements applied successfully.",
        "creditsRemaining": 99 # Will be populated by caller with actual DB state
    })
