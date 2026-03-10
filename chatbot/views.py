from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json
import re
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

        # Last fallback: Ollama (local on-system, no API key required)
        if getattr(settings, 'OLLAMA_ENABLED', False):
            self.providers.append({
                'name': 'Ollama',
                'api_url': getattr(settings, 'OLLAMA_API_ENDPOINT', 'http://localhost:11434/v1/chat/completions'),
                'api_key': 'ollama',  # Ollama ignores Authorization header but field must be non-empty
                'model': getattr(settings, 'OLLAMA_MODEL', 'llama3.2'),
                'headers_extra': {},
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
                'name': 'NPDC',
                'full_name': 'National Polar Data Center',
                'organizer': 'National Centre for Polar and Ocean Research',
                'ministry': 'Ministry of Earth Sciences, Government of India',
                'location': 'Goa, India',
                'email': 'npdc@ncpor.res.in',
                'website': 'https://www.npdc.ncpor.res.in/',
                'purpose': 'Managing and archiving scientific datasets from Polar regions and Himalaya to support research and data sharing.',
            },
            'expedition_types': [
                {'type': 'antarctic', 'name': 'Antarctic Expeditions', 'description': 'Scientific expeditions to Antarctica for research on climate, glaciology, marine biology, and more.'},
                {'type': 'arctic', 'name': 'Arctic Expeditions', 'description': 'Research expeditions to the Arctic region studying ice dynamics, ocean currents, and polar ecosystems.'},
                {'type': 'southern_ocean', 'name': 'Southern Ocean Expeditions', 'description': 'Marine research expeditions in the Southern Ocean studying oceanography and marine life.'},
                {'type': 'himalaya', 'name': 'Himalayan Expeditions', 'description': 'High-altitude research in the Himalayas focusing on glaciology, climate change, and mountain ecosystems.'},
            ],
            'categories': [
                'Agriculture',
                'Atmosphere',
                'Biological Classification',
                'Biosphere',
                'Climate Indicators',
                'Cryosphere',
                'Human Dimensions',
                'Land Surface',
                'Marine Science',
                'Oceans',
                'Paleoclimate',
                'Solid Earth',
                'Spectral/Engineering',
                'Sun-Earth Interactions',
                'Terrestrial Hydrosphere',
                'Terrestrial Science',
                'Wind Profiler Radar',
                'Geotectonic Studies',
                'Audio Signals',
            ],
            'submission_steps': [
                'Log in to your NPDC account (account must be verified and approved by NPDC)',
                'Read the submission instructions at /data/submit/instructions/',
                'Fill in the metadata form: title, abstract, keywords, expedition type, project details, temporal and spatial coverage',
                'On the next step, upload datasets (raw / actual data)',
                'Submitted metadata will be reviewed prior to publish at NPDC',
            ],
            'contact': {
                'name': 'National Polar Data Center',
                'email': 'npdc@ncpor.res.in',
                'phone': '0091-832-2525515',
                'address': 'Headland Sada, Vasco-da-Gama, Goa, INDIA - 403 804',
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
            },
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
            approved_datasets = DatasetSubmission.objects.filter(status='published').count()
            pending_datasets = DatasetSubmission.objects.filter(status__in=['submitted', 'under_review']).count()
            revision_datasets = DatasetSubmission.objects.filter(status='revision').count()
            draft_datasets = DatasetSubmission.objects.filter(status='draft').count()
            
            # Get expedition type breakdown
            expedition_counts = DatasetSubmission.objects.values('expedition_type').annotate(count=Count('id'))
            
            # Get category breakdown
            category_counts = DatasetSubmission.objects.values('category').annotate(count=Count('id'))
            
            return {
                'total_datasets': total_datasets,
                'approved_datasets': approved_datasets,
                'pending_datasets': pending_datasets,
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
            stats_text += f"\n  • Published: {stats['approved_datasets']}"
            stats_text += f"\n  • Pending Review: {stats['pending_datasets']}"
            stats_text += f"\n  • Needs Revision: {stats['revision_datasets']}"
            stats_text += f"\n  • Drafts: {stats['draft_datasets']}"
            
            if stats['expedition_counts']:
                stats_text += "\n\nBy Expedition Type:"
                for exp_type, count in stats['expedition_counts'].items():
                    stats_text += f"\n  • {exp_type.replace('_', ' ').title()}: {count}"
            
            if stats['category_counts']:
                stats_text += "\n\nBy Category:"
                for category, count in sorted(stats['category_counts'].items(), key=lambda x: x[1], reverse=True)[:5]:
                    stats_text += f"\n  • {category}: {count}"
            
            stats_text += "\n\nStatuses: Published (live), Needs Revision (awaiting submitter), Pending Review (submitted/under_review), Draft (not yet submitted)."
            stats_text += "\n\nUSE THESE EXACT NUMBERS when answering questions about dataset counts."
        
        # Regular users and guests only see approved datasets
        else:
            stats_text = "\n\n=== CURRENT DATASET STATISTICS (PUBLIC VIEW) ==="
            stats_text += f"\nPublicly Available Datasets: {stats['approved_datasets']} (Published)"
            
            # Filter expedition counts to only show approved
            from data_submission.models import DatasetSubmission
            approved_expedition_counts = DatasetSubmission.objects.filter(
                status='published'
            ).values('expedition_type').annotate(count=Count('id'))
            
            if approved_expedition_counts:
                stats_text += "\n\nBy Expedition Type:"
                for item in approved_expedition_counts:
                    exp_type = item['expedition_type']
                    count = item['count']
                    stats_text += f"\n  • {exp_type.replace('_', ' ').title()}: {count}"
            
            stats_text += "\n\nUSE THESE EXACT NUMBERS when answering questions about available datasets."
            if user_type == 'guest':
                stats_text += "\n(Note: User is not logged in - only show published/public datasets)"
        
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
            categories = ', '.join(kb['categories'])
            
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
                
                # Add page-specific admin guidance (compact)
                if page_type == 'review_list':
                    user_context += "\nTASK: Review Queue — click REVIEW to examine, EDIT to modify. Actions: APPROVE, REQUEST CHANGES, REJECT."
                elif page_type == 'review_detail':
                    user_context += "\nTASK: Evaluating submission — verify metadata, files (Metadata/Data/README), resolution. Actions: APPROVE (publish), REQUEST CHANGES (feedback), REJECT."
                elif page_type == 'admin_dashboard':
                    user_context += "\nDASHBOARD: Stats by status/expedition/category, pending count, quick links to review queue."
                
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

NPDC manages scientific datasets from polar and Himalayan research. We provide dataset submission/archival, DOI assignment, and metadata standardization (ISO topics).
Statuses: draft → submitted → under_review → revision (Needs Revision) or published (final approved state). There is NO 'approved' or 'rejected' status.

REGISTRATION: Fill form at /register/ (title, name, email, password, organisation, org URL, designation). After submit, account is INACTIVE - pending NPDC approval. No email activation link. User CANNOT log in until NPDC approves. Confirmation email sent on approval.
PASSWORD RESET: Go to /forgot-password/ → enter email → receive an email containing a secure reset link (max 10 requests/hour per network) → click the link to open the reset page and choose a new password. Password must be min 8 chars with uppercase, lowercase, number, and special char (@$!%*?&).PROFILE EDIT: Go to /profile/ → edit name/organisation/designation/contact details → Save Changes. Two forms are shown at once (personal info + profile details).
SUBMISSION STEPS: 1) Log in (account must be NPDC-approved), 2) Read instructions at /data/submit/instructions/, 3) Fill metadata form (title, abstract, keywords, expedition type/year, category, dates, coordinates), 4) Upload files (data file + metadata file + README), 5) Submit for review.

Data access requests: /data/get-data/<id>/ — requester fills form, dataset emailed directly (no approval workflow).
Dataset XML export: /data/export/xml/<id>/
Polar directory: /polar-directory/ | Station detail: /station/<name>/
Browse datasets: /search/browse/keyword/ and /search/browse/location/
Dedicated AI search: /search/ai-search/ (RAG-based)"""

            # --- Conditional admin knowledge (only for admin users to save tokens) ---
            if user_type == 'admin':
                system_prompt += """

ADMIN ROLES (RBAC):
• Super Admin (is_superuser): Full access — all features + Django admin (/admin/) + dataset deletion
• Normal Admin (is_staff, no expedition type): Same minus Django admin. Can delete datasets, manage users, view logs
• Expedition Admin (is_staff + expedition type): ONLY see/review own expedition's datasets. NO user mgmt, logs, or deletion

ADMIN PANEL (/data/admin/dashboard/):
All: Dashboard, All Datasets (/data/admin/all/), Review Queue (/data/admin/review/), Data Requests (/data/admin/data-requests/)
Super+Normal: User Approvals (/staff/user-approval/), Create Admin (/staff/create-user/), System Log (/logs/system-logs/), System Report (/logs/system-report/)

REVIEW: Submitted → Published (direct). Email sent to submitter. Audit: reviewed_by + reviewed_at.
USERS: Approve/reject at /staff/user-approval/. View/Edit/Change Password. Request Info (email). Create users at /staff/create-user/.
DATASETS: Edit at /data/admin/edit/<id>/. Delete at /data/admin/delete/<id>/ (Super+Normal only)."""

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
            base_urls = "/ (Home), /register/, /login/, /forgot-password/, /data/submit/, /data/submit/instructions/, /data/my-submissions/, /profile/, /search/, /search/ai-search/, /search/browse/keyword/, /search/browse/location/, /polar-directory/, https://www.ncpor.res.in/, mailto:npdc@ncpor.res.in, tel:0091-832-2525515"
            if user_type == 'admin':
                base_urls += ", /data/admin/dashboard/, /data/admin/all/, /data/admin/review/, /data/admin/data-requests/, /staff/user-approval/, /staff/create-user/, /logs/system-logs/, /logs/system-report/"

            system_prompt += f"""

RULES:
• HTML only: <strong>, <br>, • for lists, <a href='URL' style='color: #00A3A1;'>. NO markdown (**, ##, *)
• Never self-introduce unless asked "who are you"/"what is your name". Answer directly
• Off-topic: brief answer + redirect to NPDC
• Valid URLs ONLY: {base_urls}
• NCPOR website link only when specifically asked about NCPOR
• Contact: NCPOR, Headland Sada, Vasco-da-Gama, Goa 403804 | 0091-832-2525515 | npdc@ncpor.res.in
• Keep responses focused, HTML formatted
• For numbered steps: ALWAYS use <ol><li>short text</li></ol> tags. Keep each step to ONE short line — no long sentences, no sub-bullets inside steps
• Never use plain "1. 2. 3." for steps — always use <ol><li> tags"""

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
                            try:
                                ai_response = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', ai_response)
                                ai_response = re.sub(r'#+\s*', '', ai_response)
                                ai_response = re.sub(r'^\s*[\*\-]\s+', '• ', ai_response, flags=re.MULTILINE)

                                # Convert markdown numbered lists (1. text) to <ol><li> HTML
                                lines = ai_response.split('\n')
                                new_lines = []
                                in_list = False
                                for line in lines:
                                    m = re.match(r'^\s*\d+\.\s+(.+)$', line)
                                    if m:
                                        if not in_list:
                                            new_lines.append('<ol>')
                                            in_list = True
                                        new_lines.append(f'<li>{m.group(1)}</li>')
                                    else:
                                        if in_list:
                                            new_lines.append('</ol>')
                                            in_list = False
                                        new_lines.append(line)
                                if in_list:
                                    new_lines.append('</ol>')
                                ai_response = '\n'.join(new_lines)

                                if '<br>' not in ai_response and '\n\n' in ai_response:
                                    ai_response = ai_response.replace('\n\n', '<br><br>')
                                if '<br>' not in ai_response and '\n' in ai_response:
                                    ai_response = ai_response.replace('\n', '<br>')

                                # Remove stray <br> tags inside ol/li structure
                                ai_response = re.sub(r'<ol>\s*(?:<br>)*\s*<li>', '<ol><li>', ai_response)
                                ai_response = re.sub(r'</li>\s*(?:<br>)*\s*<li>', '</li><li>', ai_response)
                                ai_response = re.sub(r'</li>\s*(?:<br>)*\s*</ol>', '</li></ol>', ai_response)
                            except Exception as post_err:
                                print(f"⚠️ Response post-processing error ({provider['name']}): {post_err}")
                                # Return raw response rather than skipping to next provider

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
                    response += f"• Published: {stats['approved_datasets']}<br>"
                    response += f"• Pending Review: {stats['pending_datasets']}<br>"
                    response += f"• Needs Revision: {stats['revision_datasets']}<br>"
                    response += f"• Drafts: {stats['draft_datasets']}<br><br>"
                    
                    if stats['expedition_counts']:
                        response += "<strong>By Expedition Type:</strong><br>"
                        for exp_type, count in stats['expedition_counts'].items():
                            response += f"• {exp_type.replace('_', ' ').title()}: {count}<br>"
                    
                    return response
                else:
                    response = "<strong>📊 Available Datasets</strong><br><br>"
                    response += f"<strong>Publicly Available Datasets:</strong> {stats['approved_datasets']}<br><br>"
                    
                    # Get published expedition breakdown
                    from data_submission.models import DatasetSubmission
                    approved_expedition_counts = DatasetSubmission.objects.filter(
                        status='published'
                    ).values('expedition_type').annotate(count=Count('id'))
                    
                    if approved_expedition_counts:
                        response += "<strong>By Expedition Type:</strong><br>"
                        for item in approved_expedition_counts:
                            exp_type = item['expedition_type']
                            count = item['count']
                            response += f"• {exp_type.replace('_', ' ').title()}: {count}<br>"
                    
                    if user_type == 'guest':
                        response += "<br><em>Note: Only published datasets are publicly visible. "
                        response += "<a href='/login/' style='color: #00A3A1;'>Login</a> to submit your own datasets.</em>"
                    
                    return response
            else:
                return "I'm unable to fetch statistics at the moment. Please try again later."
        
        # How to submit / submission steps (must come before generic navigation link check)
        if self.fuzzy_match(message_lower, ['how to submit', 'steps to submit', 'submission steps', 'submit dataset steps', 'submit my data', 'how do i submit', 'how to submit metadata', 'submit the metadata', 'submit metadata']):
            return (
                "<strong>📤 Submit a Dataset</strong><br><br>"
                "<ol>"
                "<li><a href='/login/' style='color: #00A3A1;'>Log in</a> — account must be NPDC approved</li>"
                "<li>Read the <a href='/data/submit/instructions/' style='color: #00A3A1;'>Submission Instructions</a></li>"
                "<li>Fill the <strong>metadata form</strong> (title, abstract, keywords, expedition, dates, location)</li>"
                "<li><strong>Upload files</strong> — data file, metadata file &amp; README</li>"
                "<li>Click <strong>Submit</strong> to send for review</li>"
                "</ol><br>"
                "<a href='/data/submit/' style='color: #00A3A1; font-weight: bold;'>→ Start Submission</a>"
            )

        # Navigation links
        if self.fuzzy_match(message_lower, ['submit link', 'submit dataset', 'new dataset', 'upload data']):
            return "<strong>📤 Submit a Dataset</strong><br><br>Submit your research data here:<br><a href='/data/submit/' style='color: #00A3A1; font-weight: bold;'>→ Submit New Dataset</a><br><br>You'll need to provide metadata, temporal/spatial coverage, and upload your data files."
        
        if self.fuzzy_match(message_lower, ['my submissions', 'my datasets', 'view submissions']):
            return "<strong>📂 Your Submissions</strong><br><br>View all your submitted datasets:<br><a href='/data/my-submissions/' style='color: #00A3A1; font-weight: bold;'>→ My Submissions</a><br><br>Track status: Draft → Submitted → Under Review → Needs Revision or Published."
        
        if self.fuzzy_match(message_lower, ['home link', 'go home', 'homepage', 'main page']):
            return "<strong>🏠 Home Page</strong><br><br>Return to the main portal:<br><a href='/' style='color: #00A3A1; font-weight: bold;'>→ Go to Home Page</a>"
        
        # Password reset
        if self.fuzzy_match(message_lower, ['reset password', 'forgot password', 'change password', 'recover password', 'lost password', 'password reset']):
            return (
                "<strong>🔑 Reset Password</strong><br><br>"
                "<ol>"
                "<li>Go to <a href='/forgot-password/' style='color: #00A3A1;'>Forgot Password</a></li>"
                "<li>Enter your registered email — a reset link will be sent (check spam)</li>"
                "<li>Click the link and choose a new password</li>"
                "</ol><br>"
                "<em>Password: min 8 chars, upper+lower+number+special (@$!%*?&)</em>"
            )

        if self.fuzzy_match(message_lower, ['profile', 'my account', 'account settings', 'edit profile', 'update profile']):
            return (
                "<strong>👤 Edit Profile</strong><br><br>"
                "<ol>"
                "<li>Go to <a href='/profile/' style='color: #00A3A1;'>Profile Page</a></li>"
                "<li>Update name, organisation, designation, or contact details</li>"
                "<li>Click <strong>Save Changes</strong></li>"
                "</ol>"
            )
        
        # Registration and account creation
        if self.fuzzy_match(message_lower, ['register', 'sign up', 'create account', 'become user', 'new account', 'how to become']):
            return (
                "<strong>📝 Register for NPDC</strong><br><br>"
                "<ol>"
                "<li>Go to <a href='/register/' style='color: #00A3A1;'>Register</a></li>"
                "<li>Fill in: name, email, password, organisation &amp; designation</li>"
                "<li>Solve the captcha and submit</li>"
                "</ol><br>"
                "<strong>⚠️ Note:</strong> Account is <strong>inactive until approved</strong> by NPDC.<br>"
                "You'll receive a confirmation email once approved."
            )
        
        if self.fuzzy_match(message_lower, ['login', 'sign in', 'log in', 'how to login']):
            return (
                "<strong>🔐 Login</strong><br><br>"
                "Go to the <a href='/login/' style='color: #00A3A1; font-weight: bold;'>Login Page</a> and enter your registered email and password.<br><br>"
                "<strong>⚠️ Note:</strong> Your account must be <strong>approved by NPDC</strong> before you can log in. "
                "New registrations are reviewed before access is granted.<br><br>"
                "<strong>Forgot your password?</strong> Use <a href='/forgot-password/' style='color: #00A3A1;'>Forgot Password</a> to receive a reset link by email.<br><br>"
                "Don't have an account? <a href='/register/' style='color: #00A3A1;'>Register here</a>"
            )
        
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
                       "You have multiple submissions awaiting review.<br><br>"
                       "<strong>Submission States:</strong><br>"
                       "• <strong>Draft</strong> - User saved but didn't submit<br>"
                       "• <strong>Submitted</strong> - Awaiting admin review<br>"
                       "• <strong>Under Review</strong> - Assigned to a reviewer<br>"
                       "• <strong>Needs Revision</strong> - Waiting for submitter changes<br>"
                       "• <strong>Published</strong> - Approved and publicly accessible<br><br>"
                       "<strong>Workflow:</strong><br>"
                       "Submitted → Under Review → (Publish / Request Changes) → Final Status")
        
        # AI tools / features
        if self.fuzzy_match(message_lower, ['ai tool', 'ai feature', 'ai helper', 'auto classify', 'smart keyword', 'abstract quality',
                                             'auto fill', 'smart form', 'spatial extractor', 'coordinate extractor',
                                             'title generator', 'purpose generator', 'resolution suggester',
                                             'reviewer assistant', 'ai submission', 'quick start']):
            ai_list = '<br>'.join([f"• {f}" for f in kb['ai_features']])
            return (
                "<strong>🤖 AI-Powered Submission Tools</strong><br><br>"
                "The submission form includes <strong>9 AI helper tools</strong> to speed up your submission:<br><br>"
                f"{ai_list}<br><br>"
                "<strong>How to use:</strong> Look for the <strong>Quick Start Panel</strong> on the submission form "
                "or the individual AI buttons next to each metadata field.<br><br>"
                "<a href='/data/submit/' style='color: #00A3A1; font-weight: bold;'>→ Open Submission Form</a>"
            )

        # Search features
        if self.fuzzy_match(message_lower, ['search dataset', 'find dataset', 'browse dataset', 'smart search',
                                             'ai search', 'penguin search', 'search feature', 'filter dataset',
                                             'search page', 'how to search', 'natural language search', 'rag search']):
            return (
                "<strong>🔍 Dataset Search Features</strong><br><br>"
                "<strong>Main Search</strong> (<a href='/search/' style='color:#00A3A1;'>/search/</a>):<br>"
                "• Full-text search with sidebar filters (Expedition Type, Category, ISO Topic, Year, Bounding Box)<br>"
                "• Use quotes for exact phrases e.g. <em>\"ice core\"</em><br>"
                "• Start with <em>10.</em> to search by DOI<br>"
                "• Browse by keyword: <a href='/search/browse/keyword/' style='color:#00A3A1;'>/search/browse/keyword/</a><br>"
                "• Browse by location: <a href='/search/browse/location/' style='color:#00A3A1;'>/search/browse/location/</a><br><br>"
                "<strong>🐧 Penguin Assist (Smart Search):</strong><br>"
                "• Toggle the <strong>Smart Search switch</strong> on the main search page<br>"
                "• Understands natural language like <em>\"glacier data from Himalaya 2024\"</em> and auto-applies filters<br>"
                "• Generates an AI summary card above results<br>"
                "• Suggests alternative terms when no results are found<br><br>"
                "<strong>Dedicated AI Search</strong> (<a href='/search/ai-search/' style='color:#00A3A1;'>/search/ai-search/</a>):<br>"
                "• RAG-based interface — ask questions in plain language to find relevant datasets"
            )

        # Data resolution
        if self.fuzzy_match(message_lower, ['resolution', 'horizontal resolution', 'vertical resolution',
                                             'temporal resolution', 'spatial resolution', 'data resolution',
                                             'resolution field', 'resolution guide']):
            return (
                "<strong>📐 Data Resolution Fields</strong><br><br>"
                f"<strong>Lat/Lon Format:</strong> {kb['resolution_guide']['lat_lon']}<br><br>"
                f"<strong>Horizontal Resolution (Spatial X-Y):</strong><br>{kb['resolution_guide']['horizontal']}<br><br>"
                f"<strong>Vertical Resolution (Spatial Z):</strong><br>{kb['resolution_guide']['vertical']}<br><br>"
                f"<strong>Temporal Resolution:</strong><br>{kb['resolution_guide']['temporal']}<br><br>"
                "<em>Tip: Use the <strong>AI Resolution Suggester</strong> on the submission form to auto-recommend values.</em>"
            )

        # Data access requests
        if self.fuzzy_match(message_lower, ['access request', 'restricted dataset', 'request data', 'embargoed',
                                             'get data', 'data request', 'request access', 'how to access']):
            return (
                "<strong>📥 Data Access Requests</strong><br><br>"
                "Published datasets can be requested by logged-in users.<br><br>"
                "<strong>How to Request Data:</strong><br>"
                "<ol>"
                "<li>Log in to your NPDC account</li>"
                "<li>Open the dataset detail page</li>"
                "<li>Click the <strong>Get Data</strong> button</li>"
                "<li>Fill in the request form (name, email, institute, country, research area, purpose)</li>"
                "<li>Submit — the dataset will be <strong>emailed directly</strong> to you</li>"
                "</ol><br>"
                "<strong>Note:</strong> All requests are logged and visible to NPDC admins for monitoring at "
                "<code>/data/admin/data-requests/</code><br><br>"
                "For queries contact <a href='mailto:npdc@ncpor.res.in' style='color:#00A3A1;'>npdc@ncpor.res.in</a>"
            )

        # Dataset export / XML
        if self.fuzzy_match(message_lower, ['export', 'xml export', 'download metadata', 'metadata xml',
                                             'export dataset', 'xml file', 'export xml']):
            return (
                "<strong>📄 Dataset XML Export</strong><br><br>"
                "Any <strong>published dataset</strong> can be exported as an XML metadata file.<br><br>"
                "<strong>URL format:</strong><br>"
                "<code>/data/export/xml/&lt;metadata_id&gt;/</code><br><br>"
                "Open a dataset's detail page and click the <strong>Export XML</strong> button, "
                "or navigate directly to the URL above with the dataset's ID."
            )

        # Polar directory / stations
        if self.fuzzy_match(message_lower, ['polar directory', 'research station', 'polar station',
                                             'station detail', 'station list', 'directory']):
            return (
                "<strong>🗺️ Polar Directory & Stations</strong><br><br>"
                "<strong>Polar Directory</strong> — lists all polar research stations and associated researchers/datasets:<br>"
                "<a href='/polar-directory/' style='color:#00A3A1; font-weight:bold;'>→ /polar-directory/</a><br><br>"
                "<strong>Station Detail</strong> — detailed page for an individual station:<br>"
                "<a href='/station/&lt;name&gt;/' style='color:#00A3A1;'>/station/&lt;name&gt;/</a><br><br>"
                "Browse stations to find datasets linked to specific research locations."
            )

        # Admin panel / admin dashboard
        if user_type == 'admin' and self.fuzzy_match(message_lower, ['admin panel', 'admin dashboard', 'admin menu', 'admin sidebar',
                                                                      'admin navigation', 'admin pages', 'admin features']):
            return (
                "<strong>🛡️ Admin Panel Overview</strong><br><br>"
                "Access the admin panel at <a href='/data/admin/dashboard/' style='color:#00A3A1; font-weight:bold;'>/data/admin/dashboard/</a><br><br>"
                "<strong>Available to All Admins:</strong><br>"
                "• <a href='/data/admin/dashboard/' style='color:#00A3A1;'>Dashboard</a> — Stats overview (pending, total, users, published)<br>"
                "• <a href='/data/admin/all/' style='color:#00A3A1;'>All Datasets</a> — Browse/filter all datasets<br>"
                "• <a href='/data/admin/review/' style='color:#00A3A1;'>Review Queue</a> — Submissions pending review<br>"
                "• <a href='/data/admin/data-requests/' style='color:#00A3A1;'>Data Requests</a> — Monitor download requests<br><br>"
                "<strong>Super Admin & Normal Admin Only:</strong><br>"
                "• <a href='/staff/user-approval/' style='color:#00A3A1;'>User Approvals</a> — Approve/reject registrations<br>"
                "• <a href='/staff/create-user/' style='color:#00A3A1;'>Create Admin/User</a> — Create new accounts<br>"
                "• <a href='/logs/system-logs/' style='color:#00A3A1;'>System Log</a> — Activity logs with CSV export<br>"
                "• <a href='/logs/system-report/' style='color:#00A3A1;'>System Report</a> — Download metrics CSV"
            )

        # Admin roles
        if self.fuzzy_match(message_lower, ['admin role', 'admin type', 'super admin', 'normal admin', 'expedition admin',
                                             'child admin', 'rbac', 'access control', 'admin permission', 'who can']):
            return (
                "<strong>🔐 Admin Roles & Access Control</strong><br><br>"
                "NPDC has <strong>3 admin types</strong>:<br><br>"
                "<strong>1. Super Admin</strong><br>"
                "• Full access to everything including Django admin (/admin/)<br>"
                "• Can delete datasets, manage all users, view system logs<br><br>"
                "<strong>2. Normal Admin</strong><br>"
                "• Same as Super Admin except no Django admin panel<br>"
                "• Can delete datasets, manage users, view system logs<br><br>"
                "<strong>3. Expedition Admin (Child Admin)</strong><br>"
                "• Assigned to one expedition type (Antarctic/Arctic/Southern Ocean/Himalaya)<br>"
                "• Can <strong>only</strong> see/review datasets of their type<br>"
                "• <strong>Cannot</strong> access user management, system logs, or delete datasets"
            )

        # User management / user approval
        if user_type == 'admin' and self.fuzzy_match(message_lower, ['user management', 'manage user', 'user approval', 'approve user',
                                                                      'reject user', 'pending user', 'create user', 'create admin',
                                                                      'new user', 'new admin', 'change user password']):
            return (
                "<strong>👥 User Management</strong><br><br>"
                "<strong>User Approval Dashboard</strong> (<a href='/staff/user-approval/' style='color:#00A3A1;'>/staff/user-approval/</a>):<br>"
                "• <strong>Pending</strong> — New registrations awaiting approval<br>"
                "• <strong>Approved</strong> — Active standard users<br>"
                "• <strong>Admin</strong> — Active staff users<br>"
                "• <strong>Rejected</strong> — Rejected registrations<br><br>"
                "<strong>Actions:</strong><br>"
                "• View/Edit user details<br>"
                "• Approve or Reject registrations<br>"
                "• Request Info — send email asking for more details<br>"
                "• Change user password<br><br>"
                "<strong>Create Users</strong> (<a href='/staff/create-user/' style='color:#00A3A1;'>/staff/create-user/</a>):<br>"
                "• Standard User — auto-approved researcher account<br>"
                "• Admin User — with optional expedition type assignment<br><br>"
                "<em>Only Super Admins and Normal Admins can access user management.</em>"
            )

        # System logs
        if user_type == 'admin' and self.fuzzy_match(message_lower, ['system log', 'activity log', 'audit log', 'system report',
                                                                      'system monitor', 'log export', 'csv export logs']):
            return (
                "<strong>📋 System Logs & Reports</strong><br><br>"
                "<strong>System Log</strong> (<a href='/logs/system-logs/' style='color:#00A3A1;'>/logs/system-logs/</a>):<br>"
                "• Tracks all system activity (logins, submissions, reviews, etc.)<br>"
                "• Filter by action type, user, and date range<br>"
                "• Export to CSV for offline analysis<br><br>"
                "<strong>System Report</strong> (<a href='/logs/system-report/' style='color:#00A3A1;'>/logs/system-report/</a>):<br>"
                "• Downloads a CSV with key metrics:<br>"
                "  - Total/active/staff/superuser counts<br>"
                "  - New users in last 30 days<br>"
                "  - Dataset counts by status<br>"
                "  - Activity log totals<br><br>"
                "<em>Only Super Admins and Normal Admins can access system logs.</em>"
            )

        # Delete dataset
        if user_type == 'admin' and self.fuzzy_match(message_lower, ['delete dataset', 'remove dataset', 'delete submission']):
            return (
                "<strong>🗑️ Delete a Dataset</strong><br><br>"
                "Datasets can be permanently deleted from the <strong>All Datasets</strong> page.<br><br>"
                "<strong>Who can delete:</strong><br>"
                "• ✅ Super Admin<br>"
                "• ✅ Normal Admin<br>"
                "• ❌ Expedition Admin (cannot delete)<br><br>"
                "<strong>How:</strong> Go to <a href='/data/admin/all/' style='color:#00A3A1;'>All Datasets</a> → "
                "find the dataset → click <strong>Delete</strong> (POST action).<br><br>"
                "<em>⚠️ This action is permanent and cannot be undone.</em>"
            )

        # DOI questions
        if self.fuzzy_match(message_lower, ['doi', 'digital object identifier', 'doi assign',
                                             'search by doi', 'doi search']):
            return (
                "<strong>🔗 DOI (Digital Object Identifier)</strong><br><br>"
                "NPDC assigns DOIs to published datasets for permanent citation.<br><br>"
                "<strong>During Submission:</strong><br>"
                "• The DOI field is <strong>optional</strong> — leave it blank if you don't have one yet<br>"
                "• NPDC may assign a DOI upon approval<br><br>"
                "<strong>Searching by DOI:</strong><br>"
                "• On the <a href='/search/' style='color:#00A3A1;'>Search Page</a>, start your query with <em>10.</em> to search by DOI<br>"
                "(e.g. <em>10.1234/npdc.2024.001</em>)"
            )

        # Keywords / GCMD
        if self.fuzzy_match(message_lower, ['keyword', 'gcmd', 'smart keyword', 'suggest keyword', 'keyword generator']):
            return (
                "<strong>🏷️ Dataset Keywords</strong><br><br>"
                "NPDC recommends using <strong>GCMD (Global Change Master Directory)</strong> keywords "
                "for maximum discoverability.<br><br>"
                "<strong>How to add keywords:</strong><br>"
                "• Type keywords in the Keywords field on the submission form<br>"
                "• Separate multiple keywords with commas<br>"
                "• Use the <strong>🤖 Smart Keywords Generator</strong> AI tool to auto-suggest GCMD-compliant keywords from your abstract<br><br>"
                "<em>Good keywords greatly improve how easily other researchers find your dataset.</em>"
            )

        # ISO Topic categories
        if self.fuzzy_match(message_lower, ['iso topic', 'iso category', 'iso standard', 'topic category']):
            iso_topics = [
                'Climatology / Meteorology / Atmosphere', 'Oceans', 'Environment',
                'Geoscientific Information', 'Imagery / Base Maps / Earth Cover',
                'Inland Waters', 'Location', 'Boundaries', 'Biota', 'Economy',
                'Elevation', 'Farming', 'Health', 'Intelligence / Military',
                'Society', 'Structure', 'Transportation', 'Utilities / Communication',
            ]
            iso_list = '<br>'.join([f"• {t}" for t in iso_topics])
            return (
                "<strong>🌐 ISO Topic Categories</strong><br><br>"
                "ISO Topic is a standardised classification used alongside the Data Category.<br><br>"
                f"{iso_list}<br><br>"
                "<em>Use the <strong>Auto-Classify</strong> AI tool on the submission form to get an automatic suggestion.</em>"
            )

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
            exp_list = '<br>'.join([f"• <strong>{e['name']}</strong> - {e['description'][:80]}" for e in kb['expedition_types']])
            return (
                f"<strong>🧊 Expedition Types</strong><br><br>"
                f"NPDC archives data from these expedition types:<br><br>{exp_list}<br><br>"
                f"Select the appropriate type when submitting your dataset."
            )
        
        # Metadata fields
        if any(word in message_lower for word in ['metadata', 'field', 'required', 'information']):
            return (
                "<strong>📋 Required Metadata Fields</strong><br><br>"
                "<strong>Identification:</strong><br>"
                "• Title (max 220 characters)<br>"
                "• Abstract (max 1000 characters)<br>"
                "• Purpose (max 1000 characters)<br>"
                "• Keywords (GCMD recommended)<br>"
                "• DOI (optional)<br><br>"
                "<strong>Project Info:</strong><br>"
                "• Expedition Type &amp; Year<br>"
                "• Project Name &amp; Number<br>"
                "• Category &amp; ISO Topic<br>"
                "• Data Progress<br><br>"
                "<strong>Coverage:</strong><br>"
                "• Temporal: Start &amp; End dates<br>"
                "• Spatial: Bounding box (West/East longitude, North/South latitude in DMS)<br><br>"
                "<strong>Files (next page):</strong><br>"
                "• Data file, Metadata file, README — all required<br><br>"
                "<em>Use AI tools on the form to auto-fill many of these fields.</em>"
            )
        
        # Categories
        if any(word in message_lower for word in ['category', 'categories', 'topic', 'science']):
            cat_list = '<br>'.join([f"• {c}" for c in kb['categories']])
            return (
                f"<strong>🔬 Data Categories ({len(kb['categories'])} total)</strong><br><br>"
                f"NPDC supports these scientific categories:<br><br>{cat_list}<br><br>"
                f"Select the most appropriate category for your dataset. "
                f"Use the <strong>Auto-Classify</strong> AI tool for an automatic suggestion."
            )
        
        # About NPDC
        if any(word in message_lower for word in ['about', 'npdc', 'what is', 'portal']):
            return (
                f"<strong>ℹ️ About NPDC</strong><br><br>"
                f"{kb['portal']['purpose']}<br><br>"
                f"<strong>Organisation:</strong> {kb['portal']['organizer']}<br>"
                f"<strong>Ministry:</strong> {kb['portal']['ministry']}<br>"
                f"<strong>Location:</strong> {kb['portal']['location']}<br><br>"
                f"We archive data from Antarctic, Arctic, Himalayan, and Southern Ocean expeditions "
                f"and provide DOI assignment, metadata standardisation, and data access management."
            )
        
        # Contact
        if any(word in message_lower for word in ['contact', 'email', 'help', 'support', 'reach', 'phone', 'call']):
            return (
                f"<strong>📧 Contact Us</strong><br><br>"
                f"<strong>{kb['contact']['name']}</strong><br><br>"
                f"<strong>📍 Address:</strong><br>{kb['contact']['address']}<br><br>"
                f"<strong>📞 Phone:</strong> <a href='tel:{kb['contact']['phone']}' style='color: #00A3A1;'>{kb['contact']['phone']}</a><br><br>"
                f"<strong>✉️ Email:</strong> <a href='mailto:{kb['contact']['email']}' style='color: #00A3A1;'>{kb['contact']['email']}</a>"
            )
        
        # Status/Review
        if any(word in message_lower for word in ['status', 'review', 'approval', 'pending']):
            return (
                "<strong>📊 Submission Status Workflow</strong><br><br>"
                "Datasets go through these stages:<br><br>"
                "• <strong>Draft</strong> — Saved but not submitted; you can edit freely<br>"
                "• <strong>Submitted</strong> — Awaiting reviewer assignment<br>"
                "• <strong>Under Review</strong> — Being evaluated by NPDC staff<br>"
                "• <strong>Needs Revision</strong> — Reviewer requested changes; update and resubmit<br>"
                "• <strong>Published</strong> — Approved and publicly accessible<br><br>"
                "<em>Note: There is no 'Approved' or 'Rejected' status — the final positive state is <strong>Published</strong>.</em><br><br>"
                "<a href='/data/my-submissions/' style='color: #00A3A1;'>→ Check Your Submissions</a>"
            )
        
        # Default response
        default_items = (
            "• 📤 Submitting datasets<br>"
            "• 🤖 AI submission tools (auto-classify, smart keywords, etc.)<br>"
            "• 🔍 Searching &amp; filtering datasets<br>"
            "• 🧊 Expedition information<br>"
            "• 📋 Metadata requirements &amp; data resolution<br>"
            "• 📊 Submission status<br>"
            "• � Data access requests<br>"
            "• 📧 Contact information<br>"
        )
        if user_type == 'admin':
            default_items += (
                "• 🛡️ Admin panel &amp; navigation<br>"
                "• 🔐 Admin roles &amp; permissions<br>"
                "• 👥 User management<br>"
                "• 📋 System logs &amp; reports<br>"
            )
        return (
            "<strong>Welcome to NPDC Portal!</strong><br><br>"
            f"I can help you with:<br>{default_items}<br>"
            "What would you like to know?"
        )
    
    def get_response(self, message, conversation_history=None):
        """Main method to get chatbot response"""
        if self.ai_enabled and self.providers:
            response = self.generate_ai_response(message)
            if not response:
                print(f"⚠️ AI returned empty response, using keyword fallback")
                response = self.generate_response(message)
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
