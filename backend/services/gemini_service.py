import os
import json
import re
import time
import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
import httpx
from backend.config import GEMINI_API_KEY
from backend.models import Message, FileData

logger = logging.getLogger("backend.gemini_service")

SYSTEM_PROMPT = """You are an expert React developer. Your job is to generate complete, working React applications based on user prompts.

RULES:
1. Always respond with a valid JSON object — no markdown fences, no extra text.
2. The JSON must match this exact shape:
{
  "assistantMessage": "<brief explanation of what you built/changed>",
  "title": "<short 2-4 word title for the app, e.g. 'Todo List App'>",
  "files": {
    "/App.js": { "code": "<full file content>" },
    "/components/SomeComponent.js": { "code": "<full file content>" }
  },
  "dependencies": {
    "some-package": "latest"
  }
}
3. Use React (functional components + hooks).
4. Use Tailwind CSS for all styling. Do not use CSS modules or inline styles unless absolutely necessary.
5. The entry point must always be /App.js and must export a default component.
6. All imports must reference files you include in "files" or packages in "dependencies".
7. Do not include react, react-dom, or tailwindcss in "dependencies" — they are always available.
8. When modifying existing code, include ALL files (both changed and unchanged) in "files".
9. Keep code clean, readable, and production-quality.
10. NEVER use `import.meta` or `import.meta.env` anywhere in generated code (it breaks browser Sandpack compilation with 'Cannot use import.meta outside a module').
11. Do NOT import `@clerk/clerk-react`, `@clerk/nextjs`, `@supabase/supabase-js`, `firebase`, or real backend auth packages that require environment variables or server keys. Simulate auth/user state (profile, settings, login/logout, avatar, dropdowns) using interactive React state (`useState`/`useContext`) with mock user data so the preview runs cleanly in Sandpack without errors.
12. If the user attaches an image, use it as a design reference and match the layout/style as closely as possible."""

def sse_event(event_type: str, payload: Dict[str, Any]) -> str:
    data = {"type": event_type, **payload}
    return f"data: {json.dumps(data)}\n\n"

def extract_thought_label(text: str) -> Optional[str]:
    bold_match = re.search(r"\*\*([^*]{4,60})\*\*", text)
    if bold_match:
        return bold_match.group(1).strip()
    
    parts = re.split(r"[.\n]", text)
    if parts:
        sentence = parts[0].strip()
        if 8 <= len(sentence) <= 80:
            return sentence
    return None

async def validate_dependencies(deps: Dict[str, str]) -> Dict[str, str]:
    valid: Dict[str, str] = {}
    if not deps:
        return valid

    forbidden_pkgs = {
        "@clerk/clerk-react", "@clerk/nextjs", "@clerk/clerk-sdk-node",
        "@clerk/express", "@clerk/backend", "@supabase/supabase-js",
        "firebase", "firebase-admin"
    }

    async with httpx.AsyncClient(timeout=1.5) as client:
        async def check_pkg(pkg: str, version: str):
            if pkg in forbidden_pkgs:
                return
            try:
                res = await client.get(f"https://registry.npmjs.org/{pkg}/latest")
                if res.status_code == 200:
                    valid[pkg] = version
            except Exception:
                pass

        tasks = [check_pkg(pkg, ver) for pkg, ver in deps.items()]
        await asyncio.gather(*tasks, return_exceptions=True)

    return valid

def trim_history(messages: List[Message]) -> List[Message]:
    if len(messages) <= 10:
        return messages
    return [messages[0]] + messages[-8:]

def build_contents(messages: List[Message], file_data: Optional[FileData]) -> List[Dict[str, Any]]:
    trimmed = trim_history(messages)
    contents = []

    for idx, msg in enumerate(trimmed):
        role = "model" if msg.role == "assistant" else "user"

        if msg.role == "user":
            text = msg.content
            if msg.imageUrl:
                text = f"[The user has attached an image. Use this URL directly in the generated app where relevant (as img src, background-image, etc.): {msg.imageUrl}]\n\n{text}"

            is_last = idx == len(trimmed) - 1
            if is_last and file_data:
                text += f"\n\nCurrent project files for context:\n{json.dumps(file_data.model_dump(), indent=2)}"

            contents.append({
                "role": role,
                "parts": [{"text": text}]
            })
        else:
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}]
            })

    return contents

async def generate_code_stream(
    messages: List[Message],
    file_data: Optional[FileData]
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Calls Gemini streaming API and yields structured events:
    - {"type": "thought", "label": ...}
    - {"type": "content", "chunk": ...}
    - {"type": "error", "message": ...}
    """
    contents = build_contents(messages, file_data)
    model_name = "gemini-2.5-flash"

    api_key = (os.getenv("GEMINI_API_KEY") or GEMINI_API_KEY or "").strip()
    yielded_any_content = False

    # Try SDK streaming with gemini-2.5-flash first
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-flash-latest"]
    sdk_succeeded = False

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key or None)

        sdk_contents = []
        for c in contents:
            parts = [types.Part.from_text(text=p["text"]) for p in c["parts"]]
            sdk_contents.append(types.Content(role=c["role"], parts=parts))

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )

        for current_model in models_to_try:
            try:
                stream = await client.aio.models.generate_content_stream(
                    model=current_model,
                    contents=sdk_contents,
                    config=config
                )

                last_emit_time = 0.0

                async for chunk in stream:
                    candidates = getattr(chunk, "candidates", None) or []
                    if not candidates:
                        continue

                    content = getattr(candidates[0], "content", None)
                    parts = getattr(content, "parts", None) or []

                    for part in parts:
                        text = getattr(part, "text", None)
                        if not text:
                            continue

                        is_thought = getattr(part, "thought", False)
                        if is_thought:
                            now = time.time()
                            if now - last_emit_time > 0.6:
                                label = extract_thought_label(text)
                                if label:
                                    yield {"type": "thought", "label": label}
                                    last_emit_time = now
                        else:
                            yield {"type": "content", "chunk": text}
                            yielded_any_content = True

                sdk_succeeded = True
                break
            except Exception as stream_err:
                logger.warning(f"SDK model {current_model} failed: {stream_err}")
                if yielded_any_content:
                    yield {"type": "reset"}
                    yielded_any_content = False
                await asyncio.sleep(0.5)

    except Exception as sdk_setup_err:
        logger.warning(f"SDK setup error: {sdk_setup_err}")

    if sdk_succeeded:
        return

    # Fallback to direct HTTP SSE streaming with Gemini REST API
    for rest_model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{rest_model}:streamGenerateContent?alt=sse&key={api_key}"
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "responseMimeType": "application/json",
                "thinkingConfig": {"thinkingBudget": 0}
            }
        }

        try:
            if yielded_any_content:
                yield {"type": "reset"}
                yielded_any_content = False

            async with httpx.AsyncClient(timeout=75.0) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        logger.warning(f"REST model {rest_model} returned {response.status_code}")
                        continue

                    last_emit_time = 0.0

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:].strip()
                        if not data_str:
                            continue
                        try:
                            chunk_json = json.loads(data_str)
                            candidates = chunk_json.get("candidates", [])
                            if not candidates:
                                continue
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for p in parts:
                                txt = p.get("text", "")
                                if not txt:
                                    continue
                                if p.get("thought", False):
                                    now = time.time()
                                    if now - last_emit_time > 0.6:
                                        label = extract_thought_label(txt)
                                        if label:
                                            yield {"type": "thought", "label": label}
                                            last_emit_time = now
                                else:
                                    yield {"type": "content", "chunk": txt}
                                    yielded_any_content = True
                        except Exception as e:
                            logger.error(f"Error parsing SSE chunk: {e}")
                    return
        except Exception as rest_err:
            logger.error(f"REST model {rest_model} failed: {rest_err}")
            if yielded_any_content:
                yield {"type": "reset"}
                yielded_any_content = False

    yield {"type": "error", "message": "Failed to connect to AI generation service."}
