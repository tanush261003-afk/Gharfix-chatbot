import os
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

load_dotenv()

# Simple text splitter to replace LangChain
class SimpleTextSplitter:
    def __init__(self, chunk_size=1000, chunk_overlap=100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def split_text(self, text):
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            if end < len(text):
                # Try to break at sentence end
                sentence_end = text.rfind('.', start, end)
                if sentence_end > start + self.chunk_size // 2:
                    end = sentence_end + 1
                else:
                    # Try to break at word boundary
                    word_end = text.rfind(' ', start, end)
                    if word_end > start + self.chunk_size // 2:
                        end = word_end
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks

class RAGChatbot:
    def __init__(self):
        # Initialize embedder + vector DB (keeping for future use)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.client = chromadb.PersistentClient(path="./chroma_db")

        # Always refresh (delete and recreate) the collection
        try:
            self.client.delete_collection("gharfix_kb_1")
        except:
            pass  # Ignore if it doesn't exist

        self.collection = self.client.create_collection("gharfix_kb_1")

        # Configure Google Gemini API
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY not set in environment.")
        genai.configure(api_key=self.api_key)

        # Choose Gemini model
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        
        # Conversation memory storage
        self.conversation_memory = {}
        
        # EMBEDDED KNOWLEDGE BASE - directly in the prompt
        self.knowledge_base = """
GharFix Services Overview - Complete Details:
1. Tailoring Services
   - Custom stitching, alterations, and repairs for men's, women's, and children's clothing.
2. Massage Services
   - Professional home massage for relaxation, therapy, and wellness.
3. NRI Services
   - End-to-end support for non-resident Indians including bill payments, maintenance, and property management.
4. Ghar Bazaar
   - Assistance with household shopping and essentials.
5. Plumbing Services
   - Repairs for leaky taps, pipe fitting, bathroom installations, and emergency plumbing.
6. Financing Services
   - Affordable loan and EMI solutions for home needs.
7. MacBook Repair Services
   - Professional repair and servicing for MacBooks and Apple devices.
8. Elderly Care
   - Compassionate elderly care at home with trained caregivers.
9. Ghar Chef
   - Book personal chefs for home-cooked meals and special events.
10. Bridal Makeup & Mehendi
    - Professional bridal makeup, hairstyling, and mehendi artists.
11. Digital Signage & Banner Services
    - Design and printing of banners, posters, and digital signage.
12. RO (Water Purifier) Services
    - Installation, repair, and maintenance of water purification systems.
13. Rituals Online
    - Online booking for religious rituals and ceremonies.
14. Electrical Services
    - Electrician services for wiring, repairs, and appliance installations.
15. Housekeeping Services
    - Deep cleaning, dusting, and sanitization of homes and offices.
16. Water Tank Cleaning
    - Professional cleaning and maintenance of overhead and underground water tanks.
17. GharMaid Services
    - Trained domestic help for daily chores, cooking, and cleaning.
18. Monthly Society Maintenance
    - Billing, payments, and regular upkeep for housing societies.
19. Professional Driver Services
    - Trained drivers for personal and business use, hourly or full-time.
SERVICE COVERAGE AREAS:
We provide services in these cities ONLY:
1. Mumbai
2. Navi Mumbai
3. Lucknow (New)
4. Bangalore
5. Chennai
6. Delhi
7. Hyderabad

We do NOT operate in cities not listed above.

AVAILABILITY: Services available 24/7
CONTACT: For booking or queries, WhatsApp or call +91 75068 55407
"""

    def add_documents(self, texts):
        """Add documents to knowledge base (keeping for compatibility)"""
        text_splitter = SimpleTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        chunks = []
        for text in texts:
            chunks.extend(text_splitter.split_text(text))

        embeddings = self.embedder.encode(chunks)

        self.collection.add(
            embeddings=embeddings.tolist(),
            documents=chunks,
            ids=[f"doc_{i}" for i in range(len(chunks))]
        )

    def add_to_memory(self, conversation_id, user_message, bot_response):
        """Add conversation to memory"""
        if conversation_id not in self.conversation_memory:
            self.conversation_memory[conversation_id] = []
        
        # Add the exchange
        self.conversation_memory[conversation_id].append({
            "user": user_message,
            "bot": bot_response
        })
        
        # Keep only last 6 exchanges to prevent memory overflow
        if len(self.conversation_memory[conversation_id]) > 6:
            self.conversation_memory[conversation_id] = self.conversation_memory[conversation_id][-6:]

    def get_conversation_context(self, conversation_id):
        """Get recent conversation history"""
        if conversation_id not in self.conversation_memory:
            return ""
        
        context_lines = []
        for exchange in self.conversation_memory[conversation_id]:
            context_lines.append(f"User: {exchange['user']}")
            context_lines.append(f"Assistant: {exchange['bot']}")
        
        return "\n".join(context_lines)

    def chat_with_rag(self, question, conversation_id="default"):
        """Chat with Gemini + Embedded Knowledge + Memory"""
        
        # Get conversation history
        conversation_history = self.get_conversation_context(conversation_id)

        # Construct prompt with embedded knowledge and memory
        prompt = f"""You are GharFix's official customer assistant. Answer clearly and concisely.
You are an AI assistant who knows everything about the services mentioned below. 
Provide one precaution to the user about the issue they are describing when appropriate.

CONVERSATION HISTORY (Remember this context):
{conversation_history}

GHARFIX COMPLETE KNOWLEDGE BASE:
{self.knowledge_base}

Rules:
- ALWAYS consider the conversation history when responding
- If a user mentioned a problem earlier, acknowledge and build on that context
- Use the information from the GharFix Knowledge Base above
- If the context is not helpful, answer generally in 2–3 sentences
- Tone: professional, supportive, and helpful
- Keep answers <5 sentences unless asked for all services
- If the user asks for ALL services → list every service from knowledge base in a numbered list
- For bookings/pricing: Please ask them to WhatsApp or call us at +91 75068 55407
- If service not available → say: "I don't think we provide that service, but please call/message at +91 75068 55407 for confirmation"
- If the user asks something about which the data shared with you is unknown to you with reference with the data clearly mention that GharFix does give that service or operate in that city yet but would be better if you connect with +91 75068 55407

Current Question: {question}

Answer:"""

        try:
            # Send to Gemini with controlled generation
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=600,
                    candidate_count=1
                )
            )
            bot_response = response.text
            
            # Add to memory
            self.add_to_memory(conversation_id, question, bot_response)
            
            return bot_response
            
        except Exception as e:
            error_response = f"Sorry, I encountered an error. Please contact +91 75068 55407. Error: {str(e)}"
            self.add_to_memory(conversation_id, question, error_response)
            return error_response

# Initialize bot + load documents
bot = RAGChatbot()

sample_docs = [
    """ GharFix Services Overview:

1. Tailoring Services
   - Custom stitching, alterations, and repairs for men's, women's, and children's clothing.
2. Massage Services
   - Professional home massage for relaxation, therapy, and wellness.
3. NRI Services
   - End-to-end support for non-resident Indians including bill payments, maintenance, and property management.
4. Ghar Bazaar
   - Assistance with household shopping and essentials.
5. Plumbing Services
   - Repairs for leaky taps, pipe fitting, bathroom installations, and emergency plumbing.
6. Financing Services
   - Affordable loan and EMI solutions for home needs.
7. MacBook Repair Services
   - Professional repair and servicing for MacBooks and Apple devices.
8. Elderly Care
   - Compassionate elderly care at home with trained caregivers.
9. Ghar Chef
   - Book personal chefs for home-cooked meals and special events.
10. Bridal Makeup & Mehendi
    - Professional bridal makeup, hairstyling, and mehendi artists.
11. Digital Signage & Banner Services
    - Design and printing of banners, posters, and digital signage.
12. RO (Water Purifier) Services
    - Installation, repair, and maintenance of water purification systems.
13. Rituals Online
    - Online booking for religious rituals and ceremonies.
14. Electrical Services
    - Electrician services for wiring, repairs, and appliance installations.
15. Housekeeping Services
    - Deep cleaning, dusting, and sanitization of homes and offices.
16. Water Tank Cleaning
    - Professional cleaning and maintenance of overhead and underground water tanks.
17. GharMaid Services
    - Trained domestic help for daily chores, cooking, and cleaning.
18. Monthly Society Maintenance
    - Billing, payments, and regular upkeep for housing societies.
19. Professional Driver Services
    - Trained drivers for personal and business use, hourly or full-time.

we provide services in the following cities:-
1.Mumbai
2.Navi Mumbai
3.Lucknow (New)
4.Bangalore
5.Chennai
6.Delhi
7.Hyderabad

service available 24/7
"""
]

bot.add_documents(sample_docs)
