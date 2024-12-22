from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import pdf_router

app = FastAPI()

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(pdf_router.router)

@app.get("/")
async def root():
    return {"status": "ok"}

@app.post("/api/query")
async def query():
    return {"message": "Test endpoint"}