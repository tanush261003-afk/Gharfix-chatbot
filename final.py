import os
from dotenv import load_dotenv
import chromadb
import google.generativeai as genai

load_dotenv()

class RAGChatbot:
    def __init__(self):
        # Configure Gemini API
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not set")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")

        # Initialize ChromaDB collection
        self.client = chromadb.PersistentClient(path="./chroma_db")
        try:
            self.client.delete_collection("gharfix_kb_1")
        except:
            pass
        self.collection = self.client.create_collection("gharfix_kb_1")

        # Conversation memory and embedded knowledge base
        self.conversation_memory = {}
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
         """Add docs using Google embeddings API"""
-        resp = genai.embedding.create(model="embed-text-2", content=texts)
+        resp = genai.embeddings.embed(model="embed-text-2", content=texts)
         embeddings = [e.embedding for e in resp.embeddings]
         self.collection.add(
             embeddings=embeddings,
             documents=texts,
             ids=[f"doc_{i}" for i in range(len(texts))]
         )

    def add_to_memory(self, cid, user, bot):
        mem = self.conversation_memory.setdefault(cid, [])
        mem.append({"user": user, "bot": bot})
        if len(mem) > 6:
            self.conversation_memory[cid] = mem[-6:]

    def get_conversation_context(self, cid):
        mem = self.conversation_memory.get(cid, [])
        return "\n".join(f"User: {e['user']}\nAssistant: {e['bot']}" for e in mem)

    def search_knowledge(self, query, n_results=5):
         """Retrieve relevant docs via embeddings & ChromaDB"""
-        resp = genai.embedding.create(model="embed-text-2", content=[query])
+        resp = genai.embeddings.embed(model="embed-text-2", content=[query])
         qvec = resp.embeddings[0].embedding
         results = self.collection.query(query_embeddings=[qvec], n_results=n_results)
         return results["documents"][0] if results["documents"] else []

    def chat_with_rag(self, question, cid="default"):
        history = self.get_conversation_context(cid)
        docs = self.search_knowledge(question)
        context = "\n".join(docs)
        prompt = f"""You are GharFix's official customer assistant. Answer clearly and concisely.

CONVERSATION HISTORY:
{history}

GHARFIX KNOWLEDGE BASE:
{self.knowledge_base}

RETRIEVED CONTEXT:
{context}

Question: {question}

Answer:"""
        try:
            resp = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4, max_output_tokens=500
                )
            )
            answer = resp.text
        except:
            answer = "Sorry, I encountered an error. Please contact +91 75068 55407."
        self.add_to_memory(cid, question, answer)
        return answer

# Initialize and load knowledge
bot = RAGChatbot()
bot.add_documents([bot.knowledge_base])

