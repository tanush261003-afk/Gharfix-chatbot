from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from final import RAGChatbot
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="GharFix Chatbot API")

# Serve frontend static files at root - index.html served automatically
app.mount("/", StaticFiles(directory="forntend", html=True), name="frontend")

# Enable CORS for all origins (configure properly for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize chatbot instance
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
        response = bot.chat_with_rag(request.message, request.conversation_id)
        return ChatResponse(
            response=response,
            conversation_id=request.conversation_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
