from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="GharFix Chatbot API")

# Serve static files (CSS, JS) at /static
app.mount("/static", StaticFiles(directory="forntend"), name="static")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gharfix.com",
        "https://www.gharfix.com",
        "http://gharfix.com",
        "http://www.gharfix.com",
        "https://gharfix-chatbot.onrender.com"
    ],
    allow_credentials=False,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

# Initialize chatbot instance
bot = None
try:
    from final import RAGChatbot
    bot = RAGChatbot()
    logger.info("✅ GharFix Chatbot initialized successfully with memory")
except Exception as e:
    logger.error(f"❌ Failed to initialize chatbot: {e}")

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not bot:
        logger.error("Chatbot not initialized")
        raise HTTPException(status_code=500, detail="Chatbot not initialized")
    
    try:
        logger.info(f"Processing chat request: {request.message[:50]}...")
        response = bot.chat_with_rag(request.message, request.conversation_id)
        return ChatResponse(
            response=response,
            conversation_id=request.conversation_id,
        )
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "chatbot_ready": bot is not None
    }

@app.get("/")
async def root():
    index_path = os.path.join("forntend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        logger.error("Frontend index.html not found")
        return {"detail": "Frontend index.html not found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

