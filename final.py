import os
from dotenv import load_dotenv
import chromadb
import google.generativeai as genai
import logging
from datetime import datetime, timezone, timedelta
import urllib.parse
import re

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
                self.model = genai.GenerativeModel("gemini-2.0-flash")  # Stable version
            except:
                self.model = genai.GenerativeModel("gemini-2.5-flash")  # Latest fallback
            
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
            
            # Valid cities/locations in India
            self.valid_locations = [
                "Mumbai", "Navi Mumbai", "Thane", "Pune", "Delhi", "New Delhi",
                "Bangalore", "Bengaluru", "Chennai", "Hyderabad", "Kolkata",
                "Lucknow", "Kanpur", "Ahmedabad", "Surat", "Jaipur", "Indore",
                "Bhopal", "Patna", "Nagpur", "Goa", "Chandigarh", "Gurgaon",
                "Noida", "Greater Noida", "Faridabad", "Ghaziabad", "Andheri",
                "Bandra", "Dadar", "Worli", "Powai", "Malad", "Borivali"
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
    
    def validate_name(self, name_input):
        """Validate name - must be 2-50 characters, only letters and spaces"""
        name_clean = name_input.strip()
        
        # Check for commands or invalid patterns
        invalid_patterns = ['list', 'show', 'service', 'help', 'what', 'how', 'price', 'rate', 'cost']
        if any(pattern in name_clean.lower() for pattern in invalid_patterns):
            return False, "That doesn't look like a name"
        
        # Check length and characters
        if len(name_clean) < 2 or len(name_clean) > 50:
            return False, "Name must be between 2-50 characters"
        
        # Allow only letters, spaces, and common name characters
        if not re.match(r'^[A-Za-z][A-Za-z\s.\']+$', name_clean):
            return False, "Name can only contain letters and spaces"
        
        return True, name_clean.title()
    
    def validate_phone(self, phone_input):
        """Validate phone - must be exactly 10 digits"""
        phone_clean = re.sub(r'[^\d]', '', phone_input.strip())
        
        # Check if exactly 10 digits
        if len(phone_clean) == 10 and phone_clean.isdigit():
            # Check if starts with valid digit (6-9 for Indian mobile)
            if phone_clean[0] in ['6', '7', '8', '9']:
                return True, phone_clean
            else:
                return False, "Indian mobile numbers start with 6, 7, 8, or 9"
        else:
            return False, "Phone number must be exactly 10 digits"
    
    def validate_location(self, location_input):
        """Validate location - check if it's a real place"""
        location_clean = location_input.strip()
        
        # Check for invalid patterns
        invalid_patterns = ['i don\'t know', 'idk', 'not sure', 'help', 'what', 'where', 'list', 'show']
        if any(pattern in location_clean.lower() for pattern in invalid_patterns):
            return False, "Please provide a valid city or area name"
        
        # Check if too short
        if len(location_clean) < 3:
            return False, "Location name is too short"
        
        # Check if location contains at least some letters
        if not re.search(r'[A-Za-z]', location_clean):
            return False, "Please enter a valid location name"
        
        # Check against known cities (fuzzy match)
        location_lower = location_clean.lower()
        for valid_loc in self.valid_locations:
            if valid_loc.lower() in location_lower or location_lower in valid_loc.lower():
                return True, valid_loc
        
        # If not in list but looks valid, accept it
        if re.match(r'^[A-Za-z\s,.-]+$', location_clean):
            return True, location_clean.title()
        
        return False, "Please enter a valid city or area name"
    
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
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        timestamp = now.strftime("%Y%m%d%H%M%S")
        return f"CHAT-{timestamp}"
    
    def send_to_whatsapp(self, lead_data):
        """Return WhatsApp link - browser will auto-open it"""
        ist = timezone(timedelta(hours=5, minutes=30))
        now = datetime.now(ist)
        
        date_str = now.strftime("%d/%m/%Y")
        time_str = now.strftime("%I:%M %p")
        
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
        
        encoded_message = urllib.parse.quote(message)
        whatsapp_link = f"https://wa.me/{self.whatsapp_number}?text={encoded_message}"
        
        return whatsapp_link
    
    def collect_lead_info(self, question, cid):
        """Handle step-by-step lead collection with validation"""
        lead = self.lead_collection.get(cid, {})
        
        # Check if user wants to exit booking flow
        exit_keywords = ['cancel', 'exit', 'stop', 'quit', 'nevermind', 'back']
        if question.strip().lower() in exit_keywords:
            if cid in self.lead_collection:
                del self.lead_collection[cid]
            return "Booking cancelled. How else can I help you today?"
        
        # Initialize lead collection
        if not lead:
            self.lead_collection[cid] = {"step": "name", "data": {}}
            return "Great! I'd love to help you book a service. Let me collect some details.\n\n👤 What's your name?\n\n(Type 'cancel' anytime to exit)"
        
        # Step 1: Collect and validate Name
        if lead["step"] == "name":
            is_valid, result = self.validate_name(question)
            
            if is_valid:
                lead["data"]["name"] = result
                lead["step"] = "phone"
                self.lead_collection[cid] = lead
                return f"Nice to meet you, {result}! 📱\n\nWhat's your 10-digit mobile number?"
            else:
                return f"❌ {result}. Please enter your full name:"
        
        # Step 2: Collect and validate Phone
        elif lead["step"] == "phone":
            is_valid, result = self.validate_phone(question)
            
            if is_valid:
                lead["data"]["phone"] = result
                lead["step"] = "service"
                self.lead_collection[cid] = lead
                return "Perfect! 🔧\n\nWhich service do you need?\n\nAvailable services:\n• Plumbing\n• Electrical\n• Cleaning\n• Massage\n• Chef\n• Tailoring\n• Elderly Care\n• Water Tank Cleaning\n• Maid Service\n• Driver Service\n\nPlease type the service name:"
            else:
                return f"❌ {result}. Please enter a valid 10-digit mobile number:"
        
        # Step 3: Collect and validate Service
        elif lead["step"] == "service":
            is_valid, matched_service = self.validate_service(question.strip())
            
            if is_valid:
                lead["data"]["service"] = matched_service
                lead["step"] = "location"
                self.lead_collection[cid] = lead
                return "Excellent choice! 📍\n\nWhat's your city or area?\n\n(Example: Mumbai, Navi Mumbai, Andheri, etc.)"
            else:
                return f"❌ Sorry, '{question.strip()}' is not available.\n\nPlease choose from:\n• Plumbing • Electrical • Cleaning\n• Massage • Chef • Tailoring\n• Elderly Care • MacBook Repair\n• Water Tank Cleaning • Maid Service\n• Driver Service • NRI Services"
        
        # Step 4: Collect and validate Location
        elif lead["step"] == "location":
            is_valid, result = self.validate_location(question)
            
            if is_valid:
                lead["data"]["location"] = result
                lead["data"]["request_id"] = self.generate_request_id()
                lead["step"] = "confirm"
                self.lead_collection[cid] = lead
                
                return f"""📋 Booking Summary:

👤 Name: {lead['data']['name']}
📱 Phone: {lead['data']['phone']}
🔧 Service: {lead['data']['service']}
📍 Location: {lead['data']['location']}
📝 Status: Interested

✅ Is this information correct?

Type "Yes" to confirm and submit.
Type "No" to start over."""
            else:
                return f"❌ {result}. Please enter your city or area:"
        
        # Step 5: Confirmation
        elif lead["step"] == "confirm":
            response = question.strip().lower()
            
            if response in ["yes", "y", "yeah", "yep", "confirm", "correct", "ok", "okay"]:
                whatsapp_link = self.send_to_whatsapp(lead["data"])
                logging.info(f"✅ Lead submitted: {lead['data']}")
                del self.lead_collection[cid]
                return f"WHATSAPP_REDIRECT:{whatsapp_link}"
            
            elif response in ["no", "n", "nope"]:
                del self.lead_collection[cid]
                return "No problem! Let's start over. Type 'book now' when you're ready."
            
            else:
                return "Please type 'Yes' to confirm or 'No' to restart."
    
    def chat_with_rag(self, question, cid="default"):
        try:
            # Check if user is in booking flow
            if cid in self.lead_collection:
                return self.collect_lead_info(question, cid)
            
            # Check if user wants to book a service
            booking_keywords = ["book", "booking", "book now", "schedule", "appointment", "service booking", "i want to book"]
            if any(keyword in question.lower() for keyword in booking_keywords):
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
- If the user asks about pricing/rates → say: "Our pricing varies by service and location. Please call +91 75068 55407 or type 'book now' to get a customized quote."
- If service not available → say: "I don't think we provide that service, but please call/message at +91 75068 55407 for confirmation."
- If the user wants to book → say: "I can help you book a service! Just type 'book now' and I'll collect your details."

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

