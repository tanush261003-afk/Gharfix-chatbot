from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from final import RAGChatbot

app = FastAPI(title="GharFix Chatbot API")

# Enable CORS for all origins (configure for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chatbot
try:
    bot = RAGChatbot()
    print("✅ GharFix Chatbot initialized successfully with memory")
except Exception as e:
    print(f"❌ Failed to initialize chatbot: {e}")
    bot = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    conversation_id: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not bot:
        raise HTTPException(status_code=500, detail="Chatbot not initialized")
    
    try:
        # Pass conversation_id to maintain memory
        response = bot.chat_with_rag(request.message, request.conversation_id)
        return ChatResponse(
            response=response,
            conversation_id=request.conversation_id
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "features": ["conversation_memory", "embedded_knowledge", "gemini_api"],
        "chatbot_ready": bot is not None
    }

@app.get("/")
async def root():
    return {
        "message": "GharFix Chatbot API", 
        "status": "online",
        "version": "2.0",
        "features": "Memory + Embedded Knowledge"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
