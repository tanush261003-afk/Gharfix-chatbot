from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os

# Import your RAGChatbot class that uses Gemini
from final import RAGChatbot  # make sure trail.py contains your updated Gemini code

app = FastAPI(title="GharFix Chatbot API")
# Serve frontend folder
app.mount("/", StaticFiles(directory="forntend", html=True), name="frontend")
# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ For dev only. Replace with your frontend URLs in prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Gemini API Key from environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY not set! Please export it before running.")

# Initialize bot with API Key
bot = RAGChatbot()

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        response = bot.chat_with_rag(request.message)
        return ChatResponse(response=response, conversation_id=request.conversation_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "GharFix API is running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)


