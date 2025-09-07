import os
from dotenv import load_dotenv
import chromadb
import google.generativeai as genai
import numpy as np

load_dotenv()

class RAGChatbot:
    def __init__(self):
        # Configure Google Gemini API
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY not set in environment.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path="./chroma_db")
        try:
            self.client.delete_collection("gharfix_kb_1")
        except:
            pass
        self.collection = self.client.create_collection("gharfix_kb_1")
        # Conversation memory
        self.conversation_memory = {}
        # Embedded knowledge base
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
        """Add documents to knowledge base using Google embeddings"""
        embeddings = []
        chunks = []
        for text in texts:
            chunks.append(text)
        resp = genai.embeddings.create(model="embed-text-2", content=chunks)
        for e in resp.embeddings:
            embeddings.append(e.embedding)
        self.collection.add(
            embeddings=embeddings,
            documents=chunks,
            ids=[f"doc_{i}" for i in range(len(chunks))]
        )

    def add_to_memory(self, conversation_id, user_message, bot_response):
        mem = self.conversation_memory.setdefault(conversation_id, [])
        mem.append({"user": user_message, "bot": bot_response})
        if len(mem) > 6:
            self.conversation_memory[conversation_id] = mem[-6:]

    def get_conversation_context(self, conversation_id):
        mem = self.conversation_memory.get(conversation_id, [])
        lines = []
        for ex in mem:
            lines.append(f"User: {ex['user']}")
            lines.append(f"Assistant: {ex['bot']}")
        return "\n".join(lines)

    def search_knowledge(self, query, n_results=5):
        """Retrieve relevant docs via embeddings & ChromaDB"""
        resp = genai.embeddings.create(model="embed-text-2", content=[query])
        qvec = resp.embeddings[0].embedding
        results = self.collection.query(query_embeddings=[qvec], n_results=n_results)
        return results['documents'][0] if results['documents'] else []

    def chat_with_rag(self, question, conversation_id="default"):
        history = self.get_conversation_context(conversation_id)
        context_docs = self.search_knowledge(question)
        context = "\n".join(context_docs)
        prompt = f"""You are GharFix's official customer assistant. Answer clearly and concisely.
You are an AI assistant who knows everything about the services listed below.

CONVERSATION HISTORY:
{history}

GHARFIX KNOWLEDGE BASE:
{self.knowledge_base}

Rules:
- Always use conversation history and knowledge base.
- If context insufficient, answer generally in 2–3 sentences.
- Tone: professional, supportive.
- Keep answers under 5 sentences unless listing all services.
- If asked for all services: list them numbered.
- For bookings/pricing: direct to "+91 75068 55407".
- If a service or city is not in the knowledge base: politely state unavailability and share contact.

Current Question: {question}

Answer:"""

        try:
            resp = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4, max_output_tokens=600, candidate_count=1
                )
            )
            text = resp.text
        except Exception as e:
            text = f"Sorry, an error occurred. Please contact +91 75068 55407."
        self.add_to_memory(conversation_id, question, text)
        return text

# Initialize and load docs
bot = RAGChatbot()
bot.add_documents([bot.knowledge_base])
