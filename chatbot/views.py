from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import requests
import difflib
from datetime import datetime
from django.db.models import Count
from django.utils import timezone


class NPDCChatbot:
    """AI-powered chatbot for National Polar Data Center using Groq (primary) + OpenRouter (fallback)"""
    
    def __init__(self):
        self.ai_enabled = getattr(settings, 'CHATBOT_AI_ENABLED', True)
        self.temperature = getattr(settings, 'OPENROUTER_TEMPERATURE', 0.7)
        self.max_tokens = getattr(settings, 'OPENROUTER_MAX_TOKENS', 800)
        self.timeout = getattr(settings, 'OPENROUTER_TIMEOUT', 60)
        
        # Build ordered list of AI providers: Groq first, OpenRouter second
        self.providers = []
        
        groq_key = getattr(settings, 'GROQ_API_KEY', '')
        if groq_key:
            self.providers.append({
                'name': 'Groq',
                'api_url': getattr(settings, 'GROQ_API_ENDPOINT', 'https://api.groq.com/openai/v1/chat/completions'),
                'api_key': groq_key,
                'model': getattr(settings, 'GROQ_MODEL', 'llama-3.1-8b-instant'),
                'headers_extra': {},  # Groq uses standard OpenAI-compatible headers
            })
        
        openrouter_key = getattr(settings, 'OPENROUTER_API_KEY', '')
        if openrouter_key:
            self.providers.append({
                'name': 'OpenRouter',
                'api_url': getattr(settings, 'OPENROUTER_API_ENDPOINT', 'https://openrouter.ai/api/v1/chat/completions'),
                'api_key': openrouter_key,
                'model': getattr(settings, 'OPENROUTER_MODEL', 'google/gemma-3-4b-it:free'),
                'headers_extra': {
                    'HTTP-Referer': 'https://npdc.ncpor.gov.in',
                    'X-Title': 'NPDC Portal Chatbot',
                },
            })
        
        # Legacy attributes for backward compatibility
        if self.providers:
            self.api_key = self.providers[0]['api_key']
            self.model = self.providers[0]['model']
            self.api_url = self.providers[0]['api_url']
        else:
            self.api_key = ''
            self.model = ''
            self.api_url = ''
        
        # Print provider info
        if self.providers:
            primary = self.providers[0]
            print(f"✅ AI Initialized: {primary['name']} (primary)")
            print(f"   Model: {primary['model']}")
            print(f"   API Key: {'***' + primary['api_key'][-4:] if primary['api_key'] else '❌ NOT SET!'}")
            if len(self.providers) > 1:
                fallback = self.providers[1]
                print(f"   Fallback: {fallback['name']} ({fallback['model']})")
        else:
            print(f"❌ No AI providers configured!")
        
        self.knowledge_base = self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Load NPDC knowledge base"""
        return {
            'portal': {
                'name': 'National Polar Data Center',
                'full_name': 'National Polar Data Center (NPDC)',
                'organizer': 'National Centre for Polar and Ocean Research (NCPOR)',
                'ministry': 'Ministry of Earth Sciences, Government of India',
                'location': 'Goa, India',
                'email': 'npdc@ncpor.res.in',
                'website': 'https://www.ncpor.res.in/',
                'purpose': 'Managing and archiving scientific datasets from polar and Himalayan expeditions to support research and data sharing.',
            },
            'expedition_types': [
                {'type': 'antarctic', 'name': 'Antarctic Expeditions', 'description': 'Scientific expeditions to Antarctica for research on climate, glaciology, marine biology, and more.'},
                {'type': 'arctic', 'name': 'Arctic Expeditions', 'description': 'Research expeditions to the Arctic region studying ice dynamics, ocean currents, and polar ecosystems.'},
                {'type': 'southern_ocean', 'name': 'Southern Ocean Expeditions', 'description': 'Marine research expeditions in the Southern Ocean studying oceanography and marine life.'},
                {'type': 'himalaya', 'name': 'Himalayan Expeditions', 'description': 'High-altitude research in the Himalayas focusing on glaciology, climate change, and mountain ecosystems.'},
            ],
            'categories': [
                'Atmosphere',
                'Biosphere',
                'Cryosphere',
                'Oceans',
                'Paleoclimate',
                'Solid Earth',
                'Land Surface',
                'Marine Science',
                'Terrestrial Science',
            ],
            'submission_steps': [
                'Log in to your NPDC account',
                'Click on "Submit New Dataset" from the Data menu',
                'Fill in the dataset identification section (title, abstract, keywords)',
                'Select expedition type and project details',
                'Enter temporal and spatial coverage information',
                'Upload your data files, metadata, and README',
                'Choose access type and license',
                'Review and submit for approval',
            ],
            'contact': {
                'name': 'National Polar Data Center (NPDC)',
                'email': 'npdc@ncpor.res.in',
                'phone': '0091-832-2525515',
                'address': 'Headland Sada, Vasco-da-Gama, Goa, INDIA - 403 804',
                'hours': 'Mon-Fri: 9:00 AM - 5:00 PM IST',
            },
            'ai_features': [
                "🐧 Auto-Fill Form (in Quick Start Panel)",
                "Generate Title and Purpose from abstract",
                "Auto-Classify (Category/Topic) from abstract",
                "Suggest Keywords (GCMD compliant)",
                "Abstract Quality Check (Score & Suggestions)",
                "Auto-Fill Coordinates (Spatial extraction)",
                "Suggest Resolution (Lat/Lon/Time)",
                "Auto-Fill Citation from Profile"
            ],
            'resolution_guide': {
                'lat_lon': "Degrees, Minutes, Seconds (Integers only, e.g. 0 Deg 1 Min 30 Sec)",
                'horizontal': "Ranges like '< 1 meter', '30m-100m', '1km-10km'",
                'vertical': "Descriptive text like '1 meter', '10 cm', 'Point'",
                'temporal': "Frequency: 'Hourly', 'Daily', 'One-time', 'Annually'"
            }
        }
    
    def get_greeting(self):
        """Return greeting message"""
        return "<strong>👋 Welcome! I'm Penguin</strong><br><br>Your intelligent assistant for the National Polar Data Center. I can help with:<br>• <a href='/data/submit/' style='color: #00A3A1;'>Submit a Dataset</a><br>• AI Submission Tools & Features<br>• Dataset Submission Process<br>• Expedition Information<br>• NPDC Portal Help<br><br>What can I help you with?"
    
    def get_quick_replies(self):
        """Return quick reply options"""
        return [
            "How do I submit a dataset?",
            "What expeditions are covered?",
            "Tell me about metadata fields",
            "About NPDC",
            "Contact information"
        ]
    
    def get_real_time_stats(self):
        """Fetch real-time statistics from database"""
        try:
            from data_submission.models import DatasetSubmission
            
            total_datasets = DatasetSubmission.objects.count()
            approved_datasets = DatasetSubmission.objects.filter(status='approved').count()
            pending_datasets = DatasetSubmission.objects.filter(status__in=['submitted', 'under_review']).count()
            rejected_datasets = DatasetSubmission.objects.filter(status='rejected').count()
            revision_datasets = DatasetSubmission.objects.filter(status='revision_requested').count()
            draft_datasets = DatasetSubmission.objects.filter(status='draft').count()
            
            # Get expedition type breakdown
            expedition_counts = DatasetSubmission.objects.values('expedition_type').annotate(count=Count('id'))
            
            # Get category breakdown
            category_counts = DatasetSubmission.objects.values('category').annotate(count=Count('id'))
            
            return {
                'total_datasets': total_datasets,
                'approved_datasets': approved_datasets,
                'pending_datasets': pending_datasets,
                'rejected_datasets': rejected_datasets,
                'revision_datasets': revision_datasets,
                'draft_datasets': draft_datasets,
                'expedition_counts': {item['expedition_type']: item['count'] for item in expedition_counts},
                'category_counts': {item['category']: item['count'] for item in category_counts},
            }
        except Exception as e:
            print(f"Error fetching stats: {e}")
            return None
    
    def get_user_specific_stats(self, user_type='guest'):
        """Get statistics appropriate for user type"""
        stats = self.get_real_time_stats()
        if not stats:
            return None
        
        # Admins see everything
        if user_type == 'admin':
            stats_text = "\n\n=== CURRENT DATASET STATISTICS (ADMIN VIEW) ==="
            stats_text += f"\nTotal Datasets: {stats['total_datasets']} (all statuses)"
            stats_text += f"\n  • Approved: {stats['approved_datasets']}"
            stats_text += f"\n  • Pending Review: {stats['pending_datasets']}"
            stats_text += f"\n  • Revision Requested: {stats['revision_datasets']}"
            stats_text += f"\n  • Rejected: {stats['rejected_datasets']}"
            stats_text += f"\n  • Drafts: {stats['draft_datasets']}"
            
            if stats['expedition_counts']:
                stats_text += "\n\nBy Expedition Type:"
                for exp_type, count in stats['expedition_counts'].items():
                    stats_text += f"\n  • {exp_type.replace('_', ' ').title()}: {count}"
            
            if stats['category_counts']:
                stats_text += "\n\nBy Category:"
                for category, count in sorted(stats['category_counts'].items(), key=lambda x: x[1], reverse=True)[:5]:
                    stats_text += f"\n  • {category}: {count}"
            
            stats_text += "\n\nUSE THESE EXACT NUMBERS when answering questions about dataset counts."
        
        # Regular users and guests only see approved datasets
        else:
            stats_text = "\n\n=== CURRENT DATASET STATISTICS (PUBLIC VIEW) ==="
            stats_text += f"\nPublicly Available Datasets: {stats['approved_datasets']}"
            
            # Filter expedition counts to only show approved
            from data_submission.models import DatasetSubmission
            approved_expedition_counts = DatasetSubmission.objects.filter(
                status='approved'
            ).values('expedition_type').annotate(count=Count('id'))
            
            if approved_expedition_counts:
                stats_text += "\n\nBy Expedition Type:"
                for item in approved_expedition_counts:
                    exp_type = item['expedition_type']
                    count = item['count']
                    stats_text += f"\n  • {exp_type.replace('_', ' ').title()}: {count}"
            
            stats_text += "\n\nUSE THESE EXACT NUMBERS when answering questions about available datasets."
            if user_type == 'guest':
                stats_text += "\n(Note: User is not logged in - only show approved/public datasets)"
        
        return stats_text
    
    def fuzzy_match(self, user_input, target_phrases, threshold=0.7):
        """Check if user input fuzzy matches any target phrase (handles typos)"""
        user_words = user_input.lower().split()
        for phrase in target_phrases:
            phrase_words = phrase.lower().split()
            # Check for direct substring match first
            if phrase.lower() in user_input.lower():
                return True
            # Check fuzzy match for each word
            for user_word in user_words:
                for phrase_word in phrase_words:
                    ratio = difflib.SequenceMatcher(None, user_word, phrase_word).ratio()
                    if ratio >= threshold and len(user_word) > 3:
                        return True
        return False
    
    def generate_ai_response(self, user_message, page_context=''):
        """Generate response using OpenRouter API"""
        try:
            print(f"🤖 Generating AI response...")
            
            kb = self.knowledge_base
            page_type = getattr(self, 'page_type', 'home')
            message_lower = user_message.lower()
            
            # Smart fallback check - bypass AI for specific questions
            if any(phrase in message_lower for phrase in ['who are you', 'what is your name', 'introduce yourself']):
                return self.generate_response(user_message)
            
            if any(phrase in message_lower for phrase in ['which page', 'what page', 'current page', 'where am i']):
                return self.generate_response(user_message)
            
            if any(phrase in message_lower for phrase in ['link for', 'give me link', 'go to', 'take me to']):
                return self.generate_response(user_message)
            
            if any(phrase in message_lower for phrase in ['become user', 'become a user', 'register', 'sign up', 'create account', 'new account']):
                return self.generate_response(user_message)
            
            # Build page context
            page_context_info = ""
            user_type = getattr(self, 'user_type', 'guest')
            
            if page_type == 'home':
                page_context_info = "\n\nCURRENT PAGE: Home Page - Main NPDC portal landing page."
            elif page_type == 'submit':
                page_context_info = "\n\nCURRENT PAGE: Dataset Submission - User is submitting a new dataset."
            elif page_type == 'my_submissions':
                if user_type == 'admin':
                    page_context_info = "\n\nCURRENT PAGE: My Submissions - Admin viewing their own submitted datasets."
                else:
                    page_context_info = "\n\nCURRENT PAGE: My Submissions - User is viewing their submitted datasets."
            elif page_type == 'dashboard':
                if user_type == 'admin':
                    page_context_info = "\n\nCURRENT PAGE: Admin Dashboard - Showing submission statistics, queue overview, and analytics."
                else:
                    page_context_info = "\n\nCURRENT PAGE: Dashboard - User's personal dashboard."
            elif page_type == 'review_list':
                page_context_info = "\n\nCURRENT PAGE: Review Queue - Admin is viewing list of submissions pending review. Each submission shows status, submitter info, and action buttons (REVIEW, EDIT). Admin can click REVIEW to examine full details and approve/reject."
            elif page_type == 'review_detail':
                page_context_info = "\n\nCURRENT PAGE: Review Detail - Admin is reviewing a specific submission in detail. Showing full metadata, files, and scientist details. Admin can approve, request changes, or reject from this view."
            elif page_type == 'admin_dashboard':
                page_context_info = "\n\nCURRENT PAGE: Admin Dashboard - Main admin interface showing submission statistics, pending review count, recent submissions, and system analytics."
            elif page_type == 'search':
                page_context_info = "\n\nCURRENT PAGE: Dataset Search Page - User is searching for datasets. This page has AI-powered Smart Search features including natural language query understanding, AI result summaries, and zero-result recovery suggestions."
            
            expedition_types = ', '.join([et['name'] for et in kb['expedition_types']])
            categories = ', '.join(kb['categories'][:6])
            
            # Build user context
            user_type = getattr(self, 'user_type', 'guest')
            user_info = getattr(self, 'user_info', {})
            
            user_context = ""
            if user_type == 'admin':
                user_context = "\n\n=== CURRENT USER CONTEXT ==="
                user_context += "\nUSER TYPE: ADMIN/STAFF MEMBER"
                if user_info.get('name'):
                    user_context += f"\nName: {user_info['name']}"
                if user_info.get('is_superuser'):
                    user_context += "\nRole: Superuser (Full admin privileges)"
                elif user_info.get('expedition_admin_type'):
                    user_context += f"\nRole: {user_info['expedition_admin_type'].title()} Expedition Admin"
                else:
                    user_context += "\nRole: Admin/Staff"
                user_context += "\n\nADMIN CAPABILITIES:\n"
                user_context += "• Review and approve/reject dataset submissions\n"
                user_context += "• Request revisions from submitters\n"
                user_context += "• Manage user accounts and permissions\n"
                user_context += "• Access admin dashboard and analytics\n"
                user_context += "• View all submissions across the portal\n"
                user_context += "• Edit submission metadata if needed\n"
                
                # Add page-specific admin guidance
                if page_type == 'review_list':
                    user_context += "\n\nADMIN TASK: REVIEWING SUBMISSIONS\n"
                    user_context += "• Current view shows submissions awaiting review\n"
                    user_context += "• Click 'REVIEW' button to examine submission details\n"
                    user_context += "• Click 'EDIT' to modify metadata before review\n"
                    user_context += "• Status badges show: Draft (not submitted), Submitted (in queue), Under Review (assigned to you)\n"
                    user_context += "• From review detail page, you can: APPROVE, REQUEST CHANGES, or REJECT"
                elif page_type == 'review_detail':
                    user_context += "\n\nADMIN TASK: EVALUATING SUBMISSION\n"
                    user_context += "• Review all metadata, files, and author information\n"
                    user_context += "• Check that all required fields are complete\n"
                    user_context += "• Verify that data resolution values are reasonable\n"
                    user_context += "• Ensure all required files (Metadata, Data, README) are uploaded\n"
                    user_context += "• Actions: APPROVE (publish dataset), REQUEST CHANGES (send feedback), REJECT (return for resubmission)\n"
                    user_context += "• Use 'REQUEST CHANGES' if metadata needs improvement or files are incomplete"
                elif page_type == 'admin_dashboard':
                    user_context += "\n\nADMIN DASHBOARD FEATURES:\n"
                    user_context += "• View submission statistics by status, expedition type, category\n"
                    user_context += "• See pending review count and average review time\n"
                    user_context += "• Access quick links to review queue\n"
                    user_context += "• Monitor system health and user activity"
                
                user_context += "\n\nProvide admin-specific guidance when answering questions."
            elif user_type == 'user':
                user_context = "\n\n=== CURRENT USER CONTEXT ==="
                user_context += "\nUSER TYPE: REGISTERED RESEARCHER/USER"
                if user_info.get('name'):
                    user_context += f"\nName: {user_info['name']}"
                if user_info.get('organisation'):
                    user_context += f"\nOrganisation: {user_info['organisation']}"
                user_context += "\n\nUSER CAPABILITIES:\n"
                user_context += "• Submit new datasets\n"
                user_context += "• View and manage own submissions\n"
                user_context += "• Track submission status\n"
                user_context += "• Update profile information"
            else:
                user_context = "\n\n=== CURRENT USER CONTEXT ==="
                user_context += "\nUSER TYPE: GUEST (Not logged in)"
                user_context += "\n\nSuggest login/registration for dataset submission."
            
            # Get user-specific statistics
            stats_context = self.get_user_specific_stats(user_type) or ""
            
            # === BUILD OPTIMIZED SYSTEM PROMPT (conditional sections) ===
            
            # Core identity + portal info (always included, compact)
            system_prompt = f"""You are Penguin, the NPDC Portal Assistant.

NPDC: {kb['portal']['name']} | {kb['portal']['organizer']} | {kb['portal']['ministry']}
Location: {kb['portal']['location']} | Purpose: {kb['portal']['purpose']}
Expedition Types: {expedition_types}
Data Categories: {categories}

NPDC manages scientific datasets from polar and Himalayan research. We provide dataset submission/archival, DOI assignment, access control (Open/Restricted/Embargoed), and metadata standardization (ISO topics)."""

            # --- Conditional AI features (only for relevant pages) ---
            if page_type == 'search':
                system_prompt += """

AI SEARCH FEATURES (current page /search/):
• Penguin Smart Search Toggle - enable/disable AI-enhanced searching
• Natural Language Queries - e.g. "show me glacier data from Himalaya 2024", auto-applies filters
• AI Search Summary - auto-generated result overviews above results
• Zero-Result Recovery - suggests alternatives, detects typos and out-of-scope queries
• Filters: Expedition Type, Category, ISO Topic, Year, Temporal Range, Bounding Box, Sort
• Tips: quotes for exact phrases, "10." for DOI, natural language with Smart Search enabled"""

            elif page_type == 'submit':
                system_prompt += """

AI SUBMISSION FEATURES (current page /data/submit/):
9 AI tools accessible via buttons next to fields:
• Auto-Classify (Category/Topic) • Smart Keywords (GCMD) • Abstract Quality Check
• Spatial Coordinate Extractor • Smart Form Pre-fill • Reviewer Assistant
• AI Title Generator • AI Purpose Generator • Data Resolution Suggester"""

            # --- Conditional Form Field Guide (only on relevant pages) ---
            if page_type == 'submit':
                system_prompt += """

DATASET SUBMISSION FIELDS:
• Metadata Title - include expedition name and data type
• Category - Atmosphere/Biosphere/Cryosphere/Oceans/etc.
• Keywords - scientific terms | Topic/ISO Topic - subject area and ISO category
• Expedition Type - Antarctic/Arctic/Southern Ocean/Himalayan | Year/No - expedition year and number
• Project Number/Name | Abstract - max 1000 chars | Purpose - max 1000 chars
• Version (e.g. "1.0") | Data Set Progress - Complete/In Progress/Planned

SPATIAL (DMS): North/South Lat (-90 to 90), East/West Lon (-180 to 180) in Deg, Min, Sec
TEMPORAL: Start/End Date (YYYY-MM-DD)
RESOLUTION: Horizontal (degrees, 0.001°-5°), Vertical (meters, 1m-1000m), Temporal (Hourly/Daily/Weekly/Monthly/Yearly)
SCIENTIST: Role, Institute, Email, Phone, Address (City/State/Country/Postal)
CITATION: Creator, Editor, Series Name, Release Date/Place, Online Resource
FILES (all 3 required): Metadata File (structure desc), Data File (max 500MB, no .exe/.php/.sh), README (text/markdown docs)"""

            elif page_type == 'register':
                system_prompt += """

REGISTRATION FIELDS:
• Title (Mr/Ms/Dr/Prof) | First/Last Name - legal name
• Email - institutional, used as username | Confirm Email
• Password - min 8 chars, upper+lower+number+special (@$!%*?&) | Confirm Password
• Organisation Name | Organisation Website (http/https URL)
• Designation - job title | Personal Profile Link (optional)
• Phone (10 digits Indian) | WhatsApp (optional)
• Address | Alternate Email (optional) | Captcha - math verification"""

            # --- Always-included context sections ---
            system_prompt += page_context_info
            system_prompt += user_context
            system_prompt += stats_context

            # --- Compact rules (always included) ---
            system_prompt += """

RULES:
• HTML only: <strong>, <br>, • for lists, <a href='URL' style='color: #00A3A1;'>. NO markdown (**, ##, *)
• Never self-introduce unless asked "who are you"/"what is your name". Answer directly
• Off-topic: brief answer + redirect to NPDC
• Valid URLs ONLY: / (Home), /register/, /login/, /data/submit/, /data/my-submissions/, /profile/, https://www.ncpor.res.in/, mailto:npdc@ncpor.res.in, tel:0091-832-2525515
• NCPOR website link only when specifically asked about NCPOR
• Contact: NCPOR, Headland Sada, Vasco-da-Gama, Goa 403804 | 0091-832-2525515 | npdc@ncpor.res.in | Mon-Fri 9AM-5PM IST
• Keep responses focused, 2-4 paragraphs, HTML formatted"""

            # --- Build messages array with proper OpenAI roles ---
            messages = [
                {'role': 'system', 'content': system_prompt}
            ]
            
            # Add page context if available
            page_info = ""
            if page_context:
                page_info = f"Page context: {page_context}\n\n"
            
            # Add conversation history as proper role messages (last 4, trimmed to 100 chars)
            conversation_history = getattr(self, 'conversation_history', [])
            if conversation_history:
                for msg in conversation_history[-4:]:
                    role = 'user' if msg.get('role') == 'user' else 'assistant'
                    content = msg.get('content', '')[:100]
                    if content:
                        messages.append({'role': role, 'content': content})
            
            # Add current user message
            user_content = f"{page_info}{user_message}" if page_info else user_message
            messages.append({'role': 'user', 'content': user_content})
            
            # Try each provider in order (Groq -> OpenRouter -> keyword fallback)
            for provider in self.providers:
                try:
                    headers = {
                        'Authorization': f'Bearer {provider["api_key"]}',
                        'Content-Type': 'application/json',
                    }
                    headers.update(provider.get('headers_extra', {}))
                    
                    payload = {
                        'model': provider['model'],
                        'messages': messages,
                        'temperature': self.temperature,
                        'max_tokens': self.max_tokens,
                    }
                    
                    response = requests.post(
                        provider['api_url'],
                        headers=headers,
                        json=payload,
                        timeout=self.timeout
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        ai_response = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                        
                        if ai_response:
                            import re
                            ai_response = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', ai_response)
                            ai_response = re.sub(r'#+\s*', '', ai_response)
                            ai_response = re.sub(r'^\s*[\*\-]\s+', '• ', ai_response, flags=re.MULTILINE)
                            
                            if '<br>' not in ai_response and '\n\n' in ai_response:
                                ai_response = ai_response.replace('\n\n', '<br><br>')
                            if '<br>' not in ai_response and '\n' in ai_response:
                                ai_response = ai_response.replace('\n', '<br>')
                            
                            print(f"✅ Response from {provider['name']} ({provider['model']})")
                            return ai_response
                        else:
                            print(f"⚠️ {provider['name']} returned empty response, trying next...")
                            continue
                    elif response.status_code == 429:
                        print(f"⚠️ {provider['name']} rate limited (429), trying next provider...")
                        continue
                    else:
                        print(f"❌ {provider['name']} error: HTTP {response.status_code}")
                        continue
                
                except requests.exceptions.ConnectionError:
                    print(f"❌ Cannot connect to {provider['name']}, trying next...")
                    continue
                
                except requests.exceptions.Timeout:
                    print(f"❌ {provider['name']} timed out, trying next...")
                    continue
                
                except Exception as e:
                    print(f"❌ {provider['name']} error: {str(e)}, trying next...")
                    continue
            
            # All providers failed, use keyword fallback
            print(f"⚠️ All AI providers failed, using keyword fallback")
            return self.generate_response(user_message)
        
        except Exception as e:
            print(f"❌ AI generation error: {str(e)}")
            return self.generate_response(user_message)
    
    def generate_response(self, user_message):
        """Fallback: Generate response using keywords"""
        message_lower = user_message.lower()
        kb = self.knowledge_base
        
        page_type = getattr(self, 'page_type', 'home')
        
        # Page identification - Enhanced for all NPDC pages
        if any(phrase in message_lower for phrase in ['which page', 'what page', 'current page', 'where am i']):
            if page_type == 'submit':
                return ("<strong>📍 Current Page: Dataset Submission</strong><br><br>"
                       "You are on the <strong>Dataset Submission Page</strong>.<br><br>"
                       "Here you can submit your research data from polar or Himalayan expeditions. "
                       "Fill in the metadata, upload files, and submit for review.<br><br>"
                       "<strong>Need help?</strong> Ask me about metadata fields or expedition types!")
            elif page_type == 'view_submission':
                return ("<strong>📍 Current Page: View Submission</strong><br><br>"
                       "You are viewing a <strong>specific dataset submission</strong> with all its details.<br><br>"
                       "You can see the metadata, files, and current status of this submission.")
            elif page_type == 'my_submissions':
                return ("<strong>📍 Current Page: My Submissions</strong><br><br>"
                       "You are on <strong>My Submissions</strong> page.<br><br>"
                       "Here you can view and track all your submitted datasets and their review status.")
            elif page_type == 'submission_success':
                return ("<strong>📍 Current Page: Submission Success</strong><br><br>"
                       "🎉 <strong>Your dataset was submitted successfully!</strong><br><br>"
                       "It will now be reviewed by our team. You can track the status in "
                       "<a href='/data/my-submissions/' style='color: #00A3A1;'>My Submissions</a>.")
            elif page_type == 'admin_dashboard':
                return ("<strong>📍 Current Page: Admin Dashboard</strong><br><br>"
                       "You are on the <strong>Admin Dashboard</strong>.<br><br>"
                       "View submission statistics and manage the review workflow.")
            elif page_type == 'review_detail':
                return ("<strong>📍 Current Page: Review Submission</strong><br><br>"
                       "You are reviewing a <strong>specific submission</strong> in detail.<br><br>"
                       "You can approve, request changes, or reject this submission.")
            elif page_type == 'review_list':
                return ("<strong>📍 Current Page: Review Queue</strong><br><br>"
                       "You are viewing the <strong>list of submissions</strong> awaiting review.<br><br>"
                       "Click on any submission to review it in detail.")
            elif page_type == 'login':
                return ("<strong>📍 Current Page: Login</strong><br><br>"
                       "You are on the <strong>Login Page</strong>.<br><br>"
                       "Enter your credentials to access your NPDC account. "
                       "Don't have an account? <a href='/register/' style='color: #00A3A1;'>Register here</a>.")
            elif page_type == 'register':
                return ("<strong>📍 Current Page: Registration</strong><br><br>"
                       "You are on the <strong>Registration Page</strong>.<br><br>"
                       "Create an account to submit and manage research datasets on NPDC.")
            elif page_type == 'profile':
                return ("<strong>📍 Current Page: Profile</strong><br><br>"
                       "You are viewing your <strong>Profile Page</strong>.<br><br>"
                       "Manage your account settings and personal information.")
            elif page_type == 'dashboard':
                return ("<strong>📍 Current Page: Dashboard</strong><br><br>"
                       "You are on your <strong>Dashboard</strong>.<br><br>"
                       "View your account overview, recent activity, and quick access to key features.")
            elif page_type == 'search':
                return ("<strong>📍 Current Page: Dataset Search</strong><br><br>"
                       "You are on the <strong>Dataset Search Page</strong> with AI-powered Smart Search.<br><br>"
                       "<strong>Features available:</strong><br>"
                       "• 🐧 <strong>Penguin Smart Search</strong> - Toggle AI-enhanced searching<br>"
                       "• <strong>Natural Language Queries</strong> - Type conversational searches<br>"
                       "• <strong>AI Summaries</strong> - Auto-generated result overviews<br>"
                       "• <strong>Smart Suggestions</strong> - Alternative queries when no results found<br><br>"
                       "Use the sidebar filters to narrow down your results!")
            else:
                return ("<strong>📍 Current Page: NPDC Portal</strong><br><br>"
                       "You are on the <strong>NPDC Portal Home Page</strong>.<br><br>"
                       "From here you can:<br>"
                       "• <a href='/data/submit/' style='color: #00A3A1;'>Submit a Dataset</a><br>"
                       "• <a href='/data/my-submissions/' style='color: #00A3A1;'>View Your Submissions</a><br>"
                       "• <a href='/profile/' style='color: #00A3A1;'>Access Your Profile</a>")
        
        # Identity questions
        if any(phrase in message_lower for phrase in ['who are you', 'what is your name', 'your name', 'introduce yourself']):
            return "<strong>👋 Hello! I'm Penguin</strong><br><br>Your intelligent assistant for the <strong>National Polar Data Center</strong>.<br><br><strong>I can help you with:</strong><br>• AI-Powered Submission Tools (Smart Keywords, Auto-Classify, Title/Purpose Generators, etc.)<br>• Submitting research datasets<br>• Understanding metadata requirements & Data Resolution fields<br>• Expedition type information<br>• Navigating the NPDC portal<br><br>What would you like to know?"
        
        # Statistics questions
        if any(phrase in message_lower for phrase in ['how many', 'total datasets', 'number of datasets', 'dataset count', 'statistics', 'stats']):
            user_type = getattr(self, 'user_type', 'guest')
            stats = self.get_real_time_stats()
            
            if stats:
                if user_type == 'admin':
                    response = "<strong>📊 Dataset Statistics (Admin View)</strong><br><br>"
                    response += f"<strong>Total Datasets:</strong> {stats['total_datasets']}<br>"
                    response += f"• Approved: {stats['approved_datasets']}<br>"
                    response += f"• Pending Review: {stats['pending_datasets']}<br>"
                    response += f"• Revision Requested: {stats['revision_datasets']}<br>"
                    response += f"• Rejected: {stats['rejected_datasets']}<br>"
                    response += f"• Drafts: {stats['draft_datasets']}<br><br>"
                    
                    if stats['expedition_counts']:
                        response += "<strong>By Expedition Type:</strong><br>"
                        for exp_type, count in stats['expedition_counts'].items():
                            response += f"• {exp_type.replace('_', ' ').title()}: {count}<br>"
                    
                    return response
                else:
                    response = "<strong>📊 Available Datasets</strong><br><br>"
                    response += f"<strong>Publicly Available Datasets:</strong> {stats['approved_datasets']}<br><br>"
                    
                    # Get approved expedition breakdown
                    from data_submission.models import DatasetSubmission
                    approved_expedition_counts = DatasetSubmission.objects.filter(
                        status='approved'
                    ).values('expedition_type').annotate(count=Count('id'))
                    
                    if approved_expedition_counts:
                        response += "<strong>By Expedition Type:</strong><br>"
                        for item in approved_expedition_counts:
                            exp_type = item['expedition_type']
                            count = item['count']
                            response += f"• {exp_type.replace('_', ' ').title()}: {count}<br>"
                    
                    if user_type == 'guest':
                        response += "<br><em>Note: Only approved datasets are publicly visible. "
                        response += "<a href='/login/' style='color: #00A3A1;'>Login</a> to submit your own datasets.</em>"
                    
                    return response
            else:
                return "I'm unable to fetch statistics at the moment. Please try again later."
        
        # Navigation links
        if self.fuzzy_match(message_lower, ['submit link', 'submit dataset', 'new dataset', 'upload data']):
            return "<strong>📤 Submit a Dataset</strong><br><br>Submit your research data here:<br><a href='/data/submit/' style='color: #00A3A1; font-weight: bold;'>→ Submit New Dataset</a><br><br>You'll need to provide metadata, temporal/spatial coverage, and upload your data files."
        
        if self.fuzzy_match(message_lower, ['my submissions', 'my datasets', 'view submissions']):
            return "<strong>📂 Your Submissions</strong><br><br>View all your submitted datasets:<br><a href='/data/my-submissions/' style='color: #00A3A1; font-weight: bold;'>→ My Submissions</a><br><br>Track status: Draft, Submitted, Under Review, Approved, or Rejected."
        
        if self.fuzzy_match(message_lower, ['home link', 'go home', 'homepage', 'main page']):
            return "<strong>🏠 Home Page</strong><br><br>Return to the main portal:<br><a href='/' style='color: #00A3A1; font-weight: bold;'>→ Go to Home Page</a>"
        
        if self.fuzzy_match(message_lower, ['profile', 'my account', 'account settings']):
            return "<strong>👤 Your Profile</strong><br><br>Manage your account:<br><a href='/profile/' style='color: #00A3A1; font-weight: bold;'>→ View Profile</a>"
        
        # Registration and account creation
        if self.fuzzy_match(message_lower, ['register', 'sign up', 'create account', 'become user', 'new account', 'how to become']):
            return ("<strong>📝 Register for NPDC</strong><br><br>"
                   "To become a user and submit datasets, you'll need to register for an account. "
                   "Please click on the <a href='/register/' style='color: #00A3A1; font-weight: bold;'>Register</a> "
                   "link. This will take you to the registration form.<br><br>"
                   "The registration form requires your personal and organizational details, including your email address, "
                   "password, and contact information. Please ensure your email address is valid as it will be used as your "
                   "username. After submitting the form, you'll receive a confirmation email – please follow the link in that "
                   "email to activate your account.")
        
        if self.fuzzy_match(message_lower, ['login', 'sign in', 'log in']):
            return "<strong>🔐 Login</strong><br><br>Access your NPDC account:<br><a href='/login/' style='color: #00A3A1; font-weight: bold;'>→ Login Page</a><br><br>Don't have an account? <a href='/register/' style='color: #00A3A1;'>Register here</a>"
        
        # ADMIN-SPECIFIC RESPONSES
        user_type = getattr(self, 'user_type', 'guest')
        if user_type == 'admin':
            # Admin review workflow
            if any(phrase in message_lower for phrase in ['approve', 'approval', 'how to approve']):
                page_type = getattr(self, 'page_type', 'home')
                if page_type in ['review_list', 'review_detail']:
                    return ("<strong>✅ Approving a Submission</strong><br><br>"
                           "<strong>Steps:</strong><br>"
                           "1. Navigate to Review Submissions page using the admin menu<br>"
                           "2. Find the dataset you want to approve in the review queue<br>"
                           "3. Click the <strong>REVIEW</strong> button to view full details<br>"
                           "4. Verify all required fields are complete:<br>"
                           "   • Metadata (title, abstract, keywords, etc.)<br>"
                           "   • Files (Metadata, Data, README all uploaded)<br>"
                           "   • Spatial/Temporal coverage defined<br>"
                           "   • Data Resolution fields reasonable<br>"
                           "5. Click <strong>APPROVE</strong> button to publish the dataset<br><br>"
                           "<strong>After Approval:</strong><br>"
                           "• Dataset becomes publicly visible in search results<br>"
                           "• Dataset assigned a DOI if configured<br>"
                           "• Submitter receives approval notification email")
                else:
                    return ("<strong>✅ How to Approve Submissions</strong><br><br>"
                           "To review and approve dataset submissions:<br><br>"
                           "1. Access the <strong>Review Submissions</strong> page from admin menu<br>"
                           "2. Browse the list of pending submissions (20 Pending shown)<br>"
                           "3. Click <strong>REVIEW</strong> to examine a submission<br>"
                           "4. Verify metadata completeness and file uploads<br>"
                           "5. Click <strong>APPROVE</strong> to publish the dataset<br><br>"
                           "Only approved datasets appear in public search results.")
            
            if any(phrase in message_lower for phrase in ['reject', 'rejection', 'how to reject', 'deny']):
                return ("<strong>❌ Rejecting a Submission</strong><br><br>"
                       "<strong>When to Reject:</strong><br>"
                       "• Metadata is incomplete or incorrect<br>"
                       "• Scientific content doesn't meet standards<br>"
                       "• Data is outside NPDC scope<br>"
                       "• Submission is duplicate<br><br>"
                       "<strong>Steps:</strong><br>"
                       "1. Go to Review Submissions page<br>"
                       "2. Click <strong>REVIEW</strong> on the submission<br>"
                       "3. Review the submission details<br>"
                       "4. Click <strong>REJECT</strong> with feedback<br><br>"
                       "<strong>Better Option - Request Changes:</strong><br>"
                       "If issues are fixable (not fundamental problems), use <strong>REQUEST CHANGES</strong> instead.<br>"
                       "This allows the submitter to revise and resubmit without losing their work.")
            
            if any(phrase in message_lower for phrase in ['request changes', 'send feedback', 'revision', 'ask submitter']):
                return ("<strong>📝 Requesting Changes from Submitter</strong><br><br>"
                       "Use this when submission has fixable issues:<br><br>"
                       "<strong>Common Reasons for Requesting Changes:</strong><br>"
                       "• Abstract needs clarification<br>"
                       "• Spatial/Temporal coverage incomplete<br>"
                       "• Keywords need improvement<br>"
                       "• README file insufficient<br>"
                       "• Data Resolution values unrealistic<br>"
                       "• Missing required documentation<br><br>"
                       "<strong>How it Works:</strong><br>"
                       "1. Click <strong>REQUEST CHANGES</strong> in review detail<br>"
                       "2. Add specific feedback about what needs fixing<br>"
                       "3. Submitter receives email with your feedback<br>"
                       "4. They can revise and resubmit from their draft<br>"
                       "5. Submission returns to your review queue<br><br>"
                       "<strong>Tip:</strong> Be specific and helpful - explain exactly what needs fixing.")
            
            if any(phrase in message_lower for phrase in ['review queue', 'pending review', 'submissions to review', 'review workflow']):
                return ("<strong>📋 Review Queue Overview</strong><br><br>"
                       "<strong>Current Status:</strong><br>"
                       "You have multiple submissions awaiting review (shown as \"20 Pending\").<br><br>"
                       "<strong>Submission States:</strong><br>"
                       "• <strong>Draft</strong> - User saved but didn't submit<br>"
                       "• <strong>Submitted</strong> - Awaiting admin assignment<br>"
                       "• <strong>Under Review</strong> - Assigned to an admin<br>"
                       "• <strong>Approved</strong> - Published and public<br>"
                       "• <strong>Rejected</strong> - Returned to submitter<br>"
                       "• <strong>Revision Requested</strong> - Waiting for submitter changes<br><br>"
                       "<strong>Workflow:</strong><br>"
                       "Submitted → Under Review → (Approve/Reject/Request Changes) → Final Status")
        
        # Dataset submission
        if any(word in message_lower for word in ['submit', 'submission', 'upload', 'how to']):
            steps = '<br>'.join([f"{i+1}. {step}" for i, step in enumerate(kb['submission_steps'])])
            return (
                f"<strong>📤 How to Submit a Dataset</strong><br><br>"
                f"{steps}<br><br>"
                f"<a href='/data/submit/' style='color: #00A3A1; font-weight: bold;'>→ Start Submission</a>"
            )
        
        # Expeditions
        if any(word in message_lower for word in ['expedition', 'antarctic', 'arctic', 'himalaya', 'southern ocean']):
            exp_list = '<br>'.join([f"• <strong>{e['name']}</strong> - {e['description'][:60]}..." for e in kb['expedition_types']])
            return (
                f"<strong>🧊 Expedition Types</strong><br><br>"
                f"NPDC archives data from these expedition types:<br><br>{exp_list}<br><br>"
                f"Select the appropriate type when submitting your dataset."
            )
        
        # Metadata
        if any(word in message_lower for word in ['metadata', 'field', 'required', 'information']):
            return (
                "<strong>📋 Required Metadata Fields</strong><br><br>"
                "<strong>Identification:</strong><br>"
                "• Title, Abstract, Purpose<br>"
                "• Keywords (GCMD recommended)<br>"
                "• DOI (optional)<br><br>"
                "<strong>Project Info:</strong><br>"
                "• Expedition Type & Year<br>"
                "• Project Name & Number<br>"
                "• Category & ISO Topic<br><br>"
                "<strong>Coverage:</strong><br>"
                "• Temporal (start/end dates)<br>"
                "• Spatial (bounding box coordinates)<br><br>"
                "<strong>Access:</strong><br>"
                "• Access Type (Open/Restricted/Embargoed)<br>"
                "• License information"
            )
        
        # Categories
        if any(word in message_lower for word in ['category', 'categories', 'topic', 'science']):
            cat_list = '<br>'.join([f"• {c}" for c in kb['categories']])
            return (
                f"<strong>🔬 Data Categories</strong><br><br>"
                f"NPDC supports these scientific categories:<br><br>{cat_list}<br><br>"
                f"Select the most appropriate category for your dataset."
            )
        
        # About NPDC
        if any(word in message_lower for word in ['about', 'npdc', 'what is', 'portal']):
            return (
                f"<strong>ℹ️ About NPDC</strong><br><br>"
                f"{kb['portal']['purpose']}<br><br>"
                f"<strong>Managed by:</strong><br>"
                f"• {kb['portal']['organizer']}<br>"
                f"• {kb['portal']['ministry']}<br><br>"
                f"We archive data from Antarctic, Arctic, Himalayan, and Southern Ocean expeditions."
            )
        
        # Contact
        if any(word in message_lower for word in ['contact', 'email', 'help', 'support', 'reach', 'phone', 'call']):
            return (
                f"<strong>📧 Contact Us</strong><br><br>"
                f"<strong>{kb['contact']['name']}</strong><br><br>"
                f"<strong>📍 Address:</strong><br>{kb['contact']['address']}<br><br>"
                f"<strong>📞 Phone:</strong> <a href='tel:{kb['contact']['phone']}' style='color: #00A3A1;'>{kb['contact']['phone']}</a><br><br>"
                f"<strong>✉️ Email:</strong> <a href='mailto:{kb['contact']['email']}' style='color: #00A3A1;'>{kb['contact']['email']}</a><br><br>"
                f"<strong>🕐 Hours:</strong> {kb['contact']['hours']}"
            )
        
        # Status/Review
        if any(word in message_lower for word in ['status', 'review', 'approval', 'pending']):
            return (
                "<strong>📊 Submission Status</strong><br><br>"
                "Datasets go through these stages:<br><br>"
                "• <strong>Draft</strong> - Saved but not submitted<br>"
                "• <strong>Submitted</strong> - Awaiting reviewer assignment<br>"
                "• <strong>Under Review</strong> - Being evaluated<br>"
                "• <strong>Approved</strong> - Published and accessible<br>"
                "• <strong>Rejected</strong> - Needs revision (can resubmit)<br><br>"
                "<a href='/data/my-submissions/' style='color: #00A3A1;'>→ Check Your Submissions</a>"
            )
        
        # Default response
        return (
            "<strong>Welcome to NPDC Portal!</strong><br><br>"
            "I can help you with:<br>"
            "• 📤 Submitting datasets<br>"
            "• 🧊 Expedition information<br>"
            "• 📋 Metadata requirements<br>"
            "• 📊 Submission status<br>"
            "• 📧 Contact information<br><br>"
            "What would you like to know?"
        )
    
    def get_response(self, message, conversation_history=None):
        """Main method to get chatbot response"""
        if self.ai_enabled and self.providers:
            response = self.generate_ai_response(message)
        else:
            response = self.generate_response(message)
        
        return {
            'message': response,
            'timestamp': datetime.now().isoformat(),
            'quick_replies': self.get_quick_replies() if len(message.strip()) < 10 else []
        }


@csrf_exempt
def chatbot_init(request):
    """Initialize chatbot with greeting and quick replies"""
    try:
        chatbot = NPDCChatbot()
        
        return JsonResponse({
            'greeting': chatbot.get_greeting(),
            'quick_replies': chatbot.get_quick_replies()
        })
    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({
            'greeting': 'Welcome to National Polar Data Center!',
            'quick_replies': []
        })


@csrf_exempt
def chatbot_message(request):
    """API endpoint to handle chatbot messages"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        page_context = data.get('page_context', '')
        page_type = data.get('page_type', 'home')
        conversation_history = data.get('conversation_history', [])  # Get conversation history
        
        if not user_message:
            return JsonResponse({'error': 'Message is required'}, status=400)
        
        # Determine user type and info
        user_type = 'guest'
        user_info = {}
        
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                user_type = 'admin'
                user_info = {
                    'name': request.user.get_full_name() or request.user.username,
                    'email': request.user.email,
                    'is_superuser': request.user.is_superuser,
                }
                # Check if they have expedition admin type
                if hasattr(request.user, 'profile') and request.user.profile.expedition_admin_type:
                    user_info['expedition_admin_type'] = request.user.profile.expedition_admin_type
            else:
                user_type = 'user'
                user_info = {
                    'name': request.user.get_full_name() or request.user.username,
                    'email': request.user.email,
                }
                if hasattr(request.user, 'profile'):
                    user_info['organisation'] = request.user.profile.organisation
        
        chatbot = NPDCChatbot()
        chatbot.page_context = page_context
        chatbot.page_type = page_type
        chatbot.conversation_history = conversation_history  # Store history in chatbot instance
        chatbot.user_type = user_type
        chatbot.user_info = user_info
        
        # Handle special commands
        if user_message.lower() == '/start':
            response = {
                'message': chatbot.get_greeting(),
                'quick_replies': chatbot.get_quick_replies(),
                'timestamp': datetime.now().isoformat()
            }
        elif user_message.lower() in ['hello', 'hi', 'hey']:
            response = {
                'message': 'Hello! How can I assist you with NPDC today?',
                'quick_replies': chatbot.get_quick_replies(),
                'timestamp': datetime.now().isoformat()
            }
        else:
            response = chatbot.get_response(user_message)
        
        return JsonResponse(response)
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        print(f"Error: {e}")
        return JsonResponse({'error': str(e)}, status=500)
