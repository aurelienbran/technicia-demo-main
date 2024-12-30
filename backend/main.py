from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
from .routers import pdf_router, chat_router

app = FastAPI(
    title="TechnicIA API",
    description="API for technical documentation analysis",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "accept", "Origin", 
                  "Access-Control-Request-Method", "Access-Control-Request-Headers"],
    expose_headers=["*"],
    max_age=600
)

app.include_router(pdf_router.router)
app.include_router(chat_router.router)

@app.get("/")
async def root():
    return {"status": "healthy"}

@app.get("/ping")
async def ping():
    return {"status": "success", "message": "pong!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)