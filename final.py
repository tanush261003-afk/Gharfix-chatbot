import os
from dotenv import load_dotenv
import chromadb
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter
import google.generativeai as genai

load_dotenv()
class RAGChatbot:
    def __init__(self):
        # Initialize embedder + vector DB
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.client = chromadb.PersistentClient(path="./chroma_db")

        # Always refresh (delete and recreate) the collection
        try:
            self.client.delete_collection("gharfix_kb_1")
        except:
            pass  # Ignore if it doesn’t exist

        self.collection = self.client.create_collection("gharfix_kb_1")

        # Configure Google Gemini API
        self.api_key = os.getenv("GEMINI_API_KEY")  # <-- Store your key as env var
        if not self.api_key:
            raise ValueError("❌ GEMINI_API_KEY not set in environment.")
        genai.configure(api_key=self.api_key)

        # Choose Gemini model
        self.model = genai.GenerativeModel("gemini-1.5-flash")

    def add_documents(self, texts):
        """Add documents to knowledge base"""
        text_splitter = RecursiveCharacterTextSplitter(
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

    def search_knowledge(self, query, n_results=5):
        """Search knowledge base"""
        query_embedding = self.embedder.encode([query])
        results = self.collection.query(
            query_embeddings=query_embedding.tolist(),
            n_results=n_results
        )
        return results['documents'][0] if results['documents'] else []

    def chat_with_rag(self, question):
        """Chat with Gemini + RAG"""
        # Get relevant context
        context_docs = self.search_knowledge(question)
        context = "\n".join(context_docs)

        # Construct prompt
        prompt = f"""You are GharFix's official customer assistant. Answer clearly and concisely.
You are an AI assistant who knows everything about the services mentioned below. 
provide one precaution to the user about the issue they are describing
GharFix Services Overview:
1. Tailoring Services
2. Massage Services
3. NRI Services
4. Ghar Bazaar
5. Plumbing Services
6. Financing Services
7. MacBook Repair Services
8. Elderly Care
9. Ghar Chef
10. Bridal Makeup & Mehendi
11. Digital Signage & Banner Services
12. RO (Water Purifier) Services
13. Rituals Online
14. Electrical Services
15. Housekeeping Services
16. Water Tank Cleaning
17. GharMaid Services
18. Monthly Society Maintenance
19. Professional Driver Services
- when asked generate the above services in a proper list format
we provide services in the following cities:-
1.Mumbai
2.Navi Mumbai
3.Lucknow (New)
4.Bangalore
5.Chennai
6.Delhi
7.Hyderabad
Rules:
- Use the information in the context below.
- If the context is not helpful, answer generally in 2–3 sentences.
- Tone: professional, supportive, and helpful.
- Keep answers <5 sentences unless asked for all services.
- If the user asks for ALL services → list every service in the context clearly (numbered).
- For bookings/pricing Please ask them to WhatsApp or call us at +91 75068 55407
- If service not available → say: "I don’t think we provide that service, but please call/message at +91 75068 55407 for confirmation".
- If the user asks something about which the data shared with you is unknow to you with reference with the data clearly mention that Gharfix
  does give that service or operate in that city yet but would be better if you connect with +91 75068 55407

Context:
{context}

Question: {question}

Answer:"""

        # Send to Gemini
        response = self.model.generate_content(prompt)

        return response.text


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


