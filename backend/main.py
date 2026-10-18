import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import CORS_ORIGINS, HOST, PORT
from backend.routes.gen_ai_code import router as gen_ai_router
from backend.routes.improve import router as improve_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

app = FastAPI(
    title="Vidhyora AI App Builder Backend",
    description="Python FastAPI backend powering Gemini code generation and Sandpack agent improvements",
    version="1.0.1"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(gen_ai_router)
app.include_router(improve_router)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "Vidhyora AI Backend"}

@app.get("/", tags=["Health"])
async def root():
    return {"message": "Vidhyora AI App Builder Python FastAPI Backend"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=True)
