from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from final import RAGChatbot
import os

app = FastAPI(title="GharFix Chatbot API")

# Serve frontend files at /static (CSS, JS, assets)
app.mount("/static", StaticFiles(directory="forntend"), name="static")

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

@app.get("/")
async def root():
    index_path = os.path.join("forntend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return {"detail": "Frontend index.html not found"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
