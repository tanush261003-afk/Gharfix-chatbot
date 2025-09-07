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

        # Init ChromaDB collection
        self.client = chromadb.PersistentClient(path="./chroma_db")
        try:
            self.client.delete_collection("gharfix_kb_1")
        except:
            pass
        self.collection = self.client.create_collection("gharfix_kb_1")

        # Memory and knowledge
        self.conversation_memory = {}
        self.knowledge_base = """<YOUR KNOWLEDGE BASE TEXT>"""

    def add_documents(self, texts):
        # Use Google embeddings instead of sentence-transformers
        resp = genai.embeddings.create(model="embed-text-2", content=texts)
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
        resp = genai.embeddings.create(model="embed-text-2", content=[query])
        qvec = resp.embeddings[0].embedding
        results = self.collection.query(query_embeddings=[qvec], n_results=n_results)
        return results["documents"][0] if results["documents"] else []

    def chat_with_rag(self, question, cid="default"):
        history = self.get_conversation_context(cid)
        docs = self.search_knowledge(question)
        context = "\n".join(docs)
        prompt = f"""You are GharFix's assistant.

History:
{history}

Knowledge:
{self.knowledge_base}

Context:
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
            answer = "Sorry, please contact +91 75068 55407."
        self.add_to_memory(cid, question, answer)
        return answer

# Initialize and load
bot = RAGChatbot()
bot.add_documents([bot.knowledge_base])
