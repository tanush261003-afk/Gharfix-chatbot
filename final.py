import os
from dotenv import load_dotenv
import chromadb
import google.generativeai as genai
import logging
from datetime import datetime, timezone, timedelta
import urllib.parse

load_dotenv()

class RAGChatbot:
    def __init__(self):
        try:
            self.api_key = os.getenv("GEMINI_API_KEY")
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY not set")
            
            genai.configure(api_key=self.api_key)
            
            # Use Gemini 2.0 Flash (or 1.5-flash if 2.0 not available yet)
            try:
                self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
            except:
                self.model = genai.GenerativeModel("gemini-1.5-flash")
            
            # ChromaDB setup
            self.client = chromadb.PersistentClient(path="./chroma_db")
            try:
                self.client.delete_collection("gharfix_kb_1")
            except:
                pass
            self.collection = self.client.create_collection("gharfix_kb_1")
            
            # Lead collection system
            self.conversation_memory = {}
            self.lead_collection = {}
            
            # GharFix WhatsApp number
            self.whatsapp_number = "917506855407"
            
            # Valid services list
            self.valid_services = [
                "Tailoring", "Massage", "NRI Services", "Ghar Bazaar", "Plumbing",
                "Financing", "MacBook Repair", "Elderly Care", "Ghar Chef", "Chef",
                "Bridal Makeup", "Mehendi", "Digital Signage", "Banner", "RO Service",
                "Water Purifier", "Rituals", "Electrical", "Housekeeping", "Cleaning",
                "Water Tank Cleaning", "GharMaid", "Maid", "Society Maintenance", "Driver"
            ]
            
            self.knowledge_base = """
GharFix Services Overview - Complete Details:
1. Tailoring Services - Custom stitching, alterations, and repairs for men's, women's, and children's clothing.
2. Massage Services - Professional home massage for relaxation, therapy, and wellness.
3. NRI Services - End-to-end support for non-resident Indians including bill payments, maintenance, and property management.
4. Ghar Bazaar - Assistance with household shopping and essentials.
5. Plumbing Services - Repairs for leaky taps, pipe fitting, bathroom installations, and emergency plumbing.
6. Financing Services - Affordable loan and EMI solutions for home needs.
7. MacBook Repair Services - Professional repair and servicing for MacBooks and Apple devices.
8. Elderly Care - Compassionate elderly care at home with trained caregivers.
9. Ghar Chef - Book personal chefs for home-cooked meals and special events.
10. Bridal Makeup & Mehendi - Professional bridal makeup, hairstyling, and mehendi artists.
11. Digital Signage & Banner Services - Design and printing of banners, posters, and digital signage.
12. RO (Water Purifier) Services - Installation, repair, and maintenance of water purification systems.
13. Rituals Online - Online booking for religious rituals and ceremonies.
14. Electrical Services - Electrician services for wiring, repairs, and appliance installations.
15. Housekeeping Services - Deep cleaning, dusting, and sanitization of homes and offices.
16. Water Tank Cleaning - Professional cleaning and maintenance of overhead and underground water tanks.
17. GharMaid Services - Trained domestic help for daily chores, cooking, and cleaning.
18. Monthly Society Maintenance - Billing, payments, and regular upkeep for housing societies.
19. Professional Driver Services - Trained drivers for personal and business use, hourly or full-time.
SERVICE COVERAGE AREAS: Mumbai, Navi Mumbai, Lucknow, Bangalore, Chennai, Delhi, Hyderabad
AVAILABILITY: Services available 24/7
CONTACT: For booking or queries, WhatsApp or call +91 75068 55407
"""
            
            self.add_documents([self.knowledge_base])
            
        except Exception as e:
            logging.error(f"Failed to initialize RAGChatbot: {str(e)}")
            raise
    
    def add_documents(self, texts):
        """Add docs using Google embeddings API"""
        try:
            resp = genai.embed_content(
                model="models/text-embedding-004",
                content=texts,
                task_type="retrieval_document"
            )
            
            raw_embedding = resp.get('embedding', [])
            
            if isinstance(raw_embedding, list):
                if len(raw_embedding) > 0 and isinstance(raw_embedding[0], (int, float)):
                    embeddings = [raw_embedding]
                else:
                    embeddings = raw_embedding
            else:
                raise ValueError(f"Unexpected embedding format: {type(raw_embedding)}")
            
            logging.info(f"Adding {len(embeddings)} embeddings to ChromaDB")
            
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                ids=[f"doc_{i}" for i in range(len(texts))]
            )
        except Exception as e:
            logging.error(f"Error adding documents: {str(e)}")
            raise
    
    def add_to_memory(self, cid, user, bot):
        mem = self.conversation_memory.setdefault(cid, [])
        mem.append({"user": user, "bot": bot})
        if len(mem) > 6:
            self.conversation_memory[cid] = mem[-6:]
    
    def get_conversation_context(self, cid):
        mem = self.conversation_memory.get(cid, [])
        return "\n".join(f"User: {e['user']}\nAssistant: {e['bot']}" for e in mem)
    
    def search_knowledge(self, query, n_results=1):
        """Retrieve relevant docs via embeddings & ChromaDB"""
        try:
            resp = genai.embed_content(
                model="models/text-embedding-004",
                content=[query],
                task_type="retrieval_query"
            )
            
            qvec = resp.get('embedding', [])
            
            if isinstance(qvec, list) and len(qvec) > 0:
                if not isinstance(qvec[0], (int, float)):
                    qvec = qvec[0]
            
            results = self.collection.query(
                query_embeddings=[qvec],
                n_results=n_results
            )
            return results["documents"][0] if results["documents"] else []
        except Exception as e:
            logging.error(f"Error searching knowledge: {str(e)}")
            return []
    
    def validate_service(self, service_input):
        """Check if service is valid, suggest alternatives if not"""
        service_lower = service_input.lower().strip()
        
        # Check for exact or partial matches
        for valid_service in self.valid_services:
            if service_lower in valid_service.lower() or valid_service.lower() in service_lower:
                return True, valid_service
        
        return False, None
    
    def generate_request_id(self):
        """Generate unique request ID with IST timezone"""
        # IST is UTC+5:30
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        timestamp = now.strftime("%Y%m%d%H%M%S")
        return f"CHAT-{timestamp}"
    
    def send_to_whatsapp(self, lead_data):
        """Return WhatsApp link - browser will auto-open it"""
        # IST is UTC+5:30
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%I:%M %p")
        
        # Create formatted message WITHOUT emoji (WhatsApp displays better)
        message = f"""NEW LEAD ALERT

Request ID: {lead_data['request_id']}
Date: {date_str}
Time: {time_str}
Customer: {lead_data['name']}
Mobile: {lead_data['phone']}
Service: {lead_data['service']}
Location: {lead_data['location']}
Status: Interested

----------------------------------
Automated by GharFix chatbot"""
        
        # URL encode the message
        encoded_message = urllib.parse.quote(message)
        
        # Generate WhatsApp link that auto-opens
        whatsapp_link = f"https://wa.me/{self.whatsapp_number}?text={encoded_message}"
        
        return whatsapp_link
    
    def collect_lead_info(self, question, cid):
        """Handle step-by-step lead collection"""
        lead = self.lead_collection.get(cid, {})
        
        # Initialize lead collection
        if not lead:
            self.lead_collection[cid] = {"step": "name", "data": {}}
            return "Great! I'd love to help you book a service. Let me collect some details.\n\n👤 What's your name?"
        
        # Step 1: Collect Name
        if lead["step"] == "name":
            lead["data"]["name"] = question.strip()
            lead["step"] = "phone"
            self.lead_collection[cid] = lead
            return f"Nice to meet you, {question.strip()}! 📱\n\nWhat's your phone number?"
        
        # Step 2: Collect Phone
        elif lead["step"] == "phone":
            lead["data"]["phone"] = question.strip()
            lead["step"] = "service"
            self.lead_collection[cid] = lead
            return "Perfect! 🔧\n\nWhich service do you need?\n\nAvailable services:\n• Plumbing\n• Electrical\n• Cleaning\n• Massage\n• Chef\n• Tailoring\n• Elderly Care\n• Water Tank Cleaning\n• Maid Service\n• Driver Service\n• And more!\n\nPlease type the service name:"
        
        # Step 3: Collect Service with validation
        elif lead["step"] == "service":
            is_valid, matched_service = self.validate_service(question.strip())
            
            if is_valid:
                lead["data"]["service"] = matched_service
                lead["step"] = "location"
                self.lead_collection[cid] = lead
                return "Excellent choice! 📍\n\nWhat's your location/address?"
            else:
                # Invalid service - suggest valid ones
                return f"Sorry, '{question.strip()}' is not a service we currently offer.\n\nOur available services are:\n• Plumbing\n• Electrical\n• Cleaning\n• Massage\n• Chef\n• Tailoring\n• Elderly Care\n• MacBook Repair\n• Water Tank Cleaning\n• Maid Service\n• Driver Service\n• NRI Services\n• Society Maintenance\n\nPlease choose from the list above:"
        
        # Step 4: Collect Location
        elif lead["step"] == "location":
            lead["data"]["location"] = question.strip()
            lead["data"]["request_id"] = self.generate_request_id()
            lead["step"] = "confirm"
            self.lead_collection[cid] = lead
            
            # Show summary WITHOUT markdown
            return f"""📋 Booking Summary:

👤 Name: {lead['data']['name']}
📱 Phone: {lead['data']['phone']}
🔧 Service: {lead['data']['service']}
📍 Location: {lead['data']['location']}
📝 Status: Interested

✅ Is this information correct?

Type "Yes" to confirm and submit your request.
Type "No" to start over."""
        
        # Step 5: Confirmation
        elif lead["step"] == "confirm":
            response = question.strip().lower()
            
            if response in ["yes", "y", "yeah", "yep", "confirm", "correct"]:
                # Generate WhatsApp link
                whatsapp_link = self.send_to_whatsapp(lead["data"])
                
                # Log the lead
                logging.info(f"✅ Lead submitted: {lead['data']}")
                
                # Clear lead collection
                del self.lead_collection[cid]
                
                # Return ONLY the WhatsApp redirect signal (frontend will auto-open it)
                return f"WHATSAPP_REDIRECT:{whatsapp_link}"
            
            elif response in ["no", "n", "nope", "cancel", "restart"]:
                del self.lead_collection[cid]
                return "No problem! Let's start over. Type 'book now' when you're ready."
            
            else:
                return "Please type 'Yes' to confirm or 'No' to cancel."
    
    def chat_with_rag(self, question, cid="default"):
        try:
            # Check if user wants to book a service or is in booking flow
            booking_keywords = ["book", "booking", "book now", "schedule", "appointment", "service booking", "i want to book"]
            
            if any(keyword in question.lower() for keyword in booking_keywords) or cid in self.lead_collection:
                return self.collect_lead_info(question, cid)
            
            history = self.get_conversation_context(cid)
            docs = self.search_knowledge(question)
            context = "\n".join(docs)
            
            prompt = f"""You are GharFix's official customer assistant. Answer clearly and concisely WITHOUT using markdown formatting.

Rules:
- Use the information in the context below.
- DO NOT use markdown formatting (no **, __, etc.)
- If the context is not helpful, answer generally in 2–3 sentences.
- Tone: professional, supportive, and helpful.
- Keep answers under 5 sentences unless asked for all services
- If the user asks for ALL services → list every service in numbered format
- If service not available → say: "I don't think we provide that service, but please call/message at +91 75068 55407 for confirmation".
- If the user wants to book a service, say: "I can help you book a service! Just type 'book now' and I'll collect your details."

CONVERSATION HISTORY:
{history}

GHARFIX KNOWLEDGE BASE:
{self.knowledge_base}

RETRIEVED CONTEXT:
{context}

Question: {question}
Answer:"""
            
            resp = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=500
                )
            )
            answer = resp.text
            
        except Exception as e:
            logging.error(f"Error in chat_with_rag: {str(e)}")
            answer = "Sorry, I encountered an error. Please contact +91 75068 55407."
        
        self.add_to_memory(cid, question, answer)
        return answer
