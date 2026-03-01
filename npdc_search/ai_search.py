"""
AI-powered search utilities for NPDC Search.
Uses OpenRouter API (same as chatbot) to enhance search with:
1. Natural Language Query Understanding
2. Zero-Result Recovery / "Did You Mean"
3. AI Search Summary / Answer Box
"""
import json
import re
import hashlib
import logging
import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Valid filter values for AI extraction (must match model choices exactly)
VALID_EXPEDITIONS = ['antarctic', 'arctic', 'southern_ocean', 'himalaya']

VALID_CATEGORIES = [
    'agriculture', 'atmosphere', 'biological_classification', 'biosphere',
    'climate_indicators', 'cryosphere', 'human_dimensions', 'land_surface',
    'oceans', 'paleoclimate', 'solid_earth', 'spectral_engineering',
    'sun_earth_interactions', 'terrestrial_hydrosphere', 'marine_science',
    'terrestrial_science', 'wind_profiler_radar', 'geotectonic_studies',
    'audio_signals',
]

VALID_ISO_TOPICS = [
    'climatologyMeteorologyAtmosphere', 'oceans', 'environment',
    'geoscientificInformation', 'imageryBaseMapsEarthCover', 'inlandWaters',
    'location', 'boundaries', 'biota', 'economy', 'elevation', 'farming',
    'health', 'intelligenceMilitary', 'society', 'structure',
    'transportation', 'utilitiesCommunication',
]

# Cache timeout for AI responses (seconds)
AI_CACHE_TIMEOUT = 900  # 15 minutes


def _call_openrouter(prompt, max_tokens=400, temperature=0.3):
    """
    Call AI API with a prompt. Tries Groq first, then OpenRouter as fallback.
    Low temperature for structured/deterministic output.
    """
    timeout = getattr(settings, 'OPENROUTER_TIMEOUT', 60)

    # Build providers list: Groq first, OpenRouter second
    providers = []

    groq_key = getattr(settings, 'GROQ_API_KEY', '')
    if groq_key:
        providers.append({
            'name': 'Groq',
            'api_url': getattr(settings, 'GROQ_API_ENDPOINT', 'https://api.groq.com/openai/v1/chat/completions'),
            'api_key': groq_key,
            'model': getattr(settings, 'GROQ_MODEL', 'llama-3.1-8b-instant'),
            'headers_extra': {},
        })

    openrouter_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if openrouter_key:
        providers.append({
            'name': 'OpenRouter',
            'api_url': getattr(settings, 'OPENROUTER_API_ENDPOINT', 'https://openrouter.ai/api/v1/chat/completions'),
            'api_key': openrouter_key,
            'model': getattr(settings, 'OPENROUTER_MODEL', 'google/gemma-3-4b-it:free'),
            'headers_extra': {
                'HTTP-Referer': 'https://npdc.ncpor.gov.in',
                'X-Title': 'NPDC AI Search',
            },
        })

    if not providers:
        logger.warning("No AI API keys configured")
        return None

    for provider in providers:
        try:
            headers = {
                'Authorization': f'Bearer {provider["api_key"]}',
                'Content-Type': 'application/json',
            }
            headers.update(provider.get('headers_extra', {}))

            payload = {
                'model': provider['model'],
                'messages': [{'role': 'user', 'content': prompt}],
                'temperature': temperature,
                'max_tokens': max_tokens,
            }

            response = requests.post(provider['api_url'], headers=headers, json=payload, timeout=timeout)
            if response.status_code == 200:
                result = response.json()
                text = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                if text:
                    return text
                logger.warning(f"{provider['name']} returned empty response, trying next...")
                continue
            elif response.status_code == 429:
                logger.warning(f"{provider['name']} rate limited (429), trying next provider...")
                continue
            else:
                logger.error(f"{provider['name']} API error: HTTP {response.status_code}")
                continue
        except requests.exceptions.Timeout:
            logger.error(f"{provider['name']} API timeout, trying next...")
            continue
        except Exception as e:
            logger.error(f"{provider['name']} API error: {e}, trying next...")
            continue

    logger.error("All AI providers failed")
    return None


# =====================================================================
# FEATURE 1: Natural Language Query Understanding
# =====================================================================

def parse_natural_language_query(user_query):
    """
    Send a natural language query to AI and get back structured search params.
    
    Input:  "glacier temperature data from Himalaya 2024"
    Output: {
        "keywords": "glacier temperature",
        "expedition": "himalaya",
        "year": "2024-2025",
        "category": "cryosphere"
    }
    """
    if not user_query or len(user_query.strip()) < 5:
        return None

    # Check cache first
    cache_key = f"ai_parse:{hashlib.md5(user_query.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    prompt = f"""You are a search query parser for the National Polar Data Center (NPDC), a scientific data repository for polar and Himalayan expedition datasets.

Parse this natural language search query into structured search parameters.

QUERY: "{user_query}"

VALID VALUES:
- expedition: {json.dumps(VALID_EXPEDITIONS)}
- category: {json.dumps(VALID_CATEGORIES)}
- iso_topic: {json.dumps(VALID_ISO_TOPICS)}
- year: Format "YYYY-YYYY+1" e.g. "2024-2025" (range: 1981-2036)

RULES:
1. Extract search keywords (core scientific terms only, remove filter words like "from", "in", "about")
2. Map location mentions to expedition type (Antarctica→antarctic, Arctic→arctic, Himalaya→himalaya, Southern Ocean→southern_ocean)
3. Map science topics to the closest category value
4. If a year is mentioned, format it as "YEAR-YEAR+1"
5. Only include fields you are confident about. Leave uncertain fields out.
6. "keywords" should contain the refined search terms for full-text search

Return ONLY valid JSON, no explanation:
{{"keywords": "...", "expedition": "...", "category": "...", "iso_topic": "...", "year": "..."}}

If nothing can be extracted, return: {{"keywords": "{user_query}"}}"""

    ai_response = _call_openrouter(prompt, max_tokens=200, temperature=0.1)
    
    if not ai_response:
        return None

    # Parse JSON from AI response
    try:
        # Try to extract JSON from response (AI sometimes wraps in markdown)
        json_match = re.search(r'\{[^{}]+\}', ai_response)
        if json_match:
            parsed = json.loads(json_match.group())
        else:
            return None

        # Validate extracted values
        result = {}
        
        if parsed.get('keywords'):
            result['keywords'] = str(parsed['keywords']).strip()[:200]
        
        if parsed.get('expedition') and parsed['expedition'] in VALID_EXPEDITIONS:
            result['expedition'] = parsed['expedition']
        
        if parsed.get('category') and parsed['category'] in VALID_CATEGORIES:
            result['category'] = parsed['category']
        
        if parsed.get('iso_topic') and parsed['iso_topic'] in VALID_ISO_TOPICS:
            result['iso_topic'] = parsed['iso_topic']
        
        if parsed.get('year'):
            year_str = str(parsed['year'])
            # Validate year format
            if re.match(r'^\d{4}-\d{4}$', year_str):
                result['year'] = year_str

        if result:
            cache.set(cache_key, result, AI_CACHE_TIMEOUT)
            return result

    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"Failed to parse AI response: {e}")

    return None


# =====================================================================
# FEATURE 2: Zero-Result Recovery / "Did You Mean"
# =====================================================================

def get_ai_suggestions(failed_query, available_keywords=None):
    """
    When a search returns 0 results, ask AI for alternative suggestions.
    
    Returns: {
        "corrected_query": "arctic ice sheet",
        "suggestions": ["Antarctic ice core", "Cryosphere data", "Ice dynamics"]
    }
    """
    if not failed_query or len(failed_query.strip()) < 3:
        return None

    cache_key = f"ai_suggest:{hashlib.md5(failed_query.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Build context about available data
    keyword_context = ""
    if available_keywords:
        keyword_context = f"\nDATASETS IN THE DATABASE CONTAIN THESE KEYWORDS/TOPICS: {', '.join(available_keywords[:30])}"

    prompt = f"""You are a search assistant for the National Polar Data Center (NPDC), a scientific data repository for polar and Himalayan expedition research.

A user searched for "{failed_query}" but got ZERO results.

The database contains datasets about:
- Antarctic, Arctic, Southern Ocean, and Himalayan expeditions
- Categories: Atmosphere, Biosphere, Cryosphere, Oceans, Paleoclimate, Solid Earth, Land Surface, Marine Science, Terrestrial Science
- Scientific research data: temperature, glaciology, marine biology, oceanography, climate, ice cores, weather, etc.{keyword_context}

Provide:
1. A corrected version of the query (fix typos, improve terms)
2. Up to 4 alternative search suggestions that ARE likely to find results in this polar/Himalayan research database

Return ONLY valid JSON:
{{"corrected_query": "...", "suggestions": ["...", "...", "...", "..."]}}

If the query is completely unrelated to polar/Himalayan science, return:
{{"corrected_query": "", "suggestions": [], "off_topic": true}}"""

    ai_response = _call_openrouter(prompt, max_tokens=250, temperature=0.3)
    
    if not ai_response:
        return None

    try:
        json_match = re.search(r'\{[^{}]*\}', ai_response, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            result = {
                'corrected_query': str(parsed.get('corrected_query', '')).strip()[:200],
                'suggestions': [str(s).strip()[:100] for s in parsed.get('suggestions', [])[:4]],
                'off_topic': parsed.get('off_topic', False),
            }
            cache.set(cache_key, result, AI_CACHE_TIMEOUT)
            return result
    except (json.JSONDecodeError, AttributeError) as e:
        logger.error(f"Failed to parse AI suggestions: {e}")

    return None


# =====================================================================
# FEATURE 3: AI Search Summary / Answer Box
# =====================================================================

def generate_search_summary(query, results, result_count):
    """
    Generate an AI summary of the top search results.
    
    Input: query string + list of top result dicts
    Output: HTML summary string
    """
    if not query or not results or result_count == 0:
        return None

    cache_key = f"ai_summary:{hashlib.md5((query + str(result_count)).encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # Build context from top results
    results_context = ""
    for i, r in enumerate(results[:5], 1):
        results_context += f"\n{i}. {r['title']}"
        results_context += f"\n   {r['category']} | {r['expedition_type']} | {r['temporal_start']} to {r['temporal_end']}"
        results_context += f"\n   {r['abstract'][:150]}"
        results_context += "\n"

    prompt = f"""You are a search assistant for NPDC (National Polar Data Center).

User searched: "{query}" — {result_count} results found.

TOP RESULTS:
{results_context}

Write a 2-3 sentence plain text summary. Be specific about dataset names, regions, and time periods. No markdown."""

    ai_response = _call_openrouter(prompt, max_tokens=200, temperature=0.5)
    
    if ai_response:
        # Clean up any markdown that slipped through
        ai_response = re.sub(r'\*\*([^*]+)\*\*', r'\1', ai_response)
        ai_response = re.sub(r'#+\s*', '', ai_response)
        ai_response = ai_response.strip()
        
        cache.set(cache_key, ai_response, AI_CACHE_TIMEOUT)
        return ai_response

    return None


def get_available_keywords():
    """
    Get a list of keywords/titles from the database for context.
    Used by the suggestion engine.
    """
    try:
        from data_submission.models import DatasetSubmission
        
        # Get unique keywords and titles
        datasets = DatasetSubmission.objects.filter(
            status='published'
        ).values_list('title', 'keywords', 'category').distinct()[:50]
        
        keywords = set()
        for title, kw, cat in datasets:
            keywords.add(title[:50])
            if kw:
                for k in kw.split(','):
                    k = k.strip()
                    if k:
                        keywords.add(k)
            keywords.add(cat)
        
        return list(keywords)[:30]
    except Exception:
        return []


# =====================================================================
# FEATURE 4: AI Search Answer (FTS + LLM — KPDC-style)
# =====================================================================

def _call_llm_chat(system_prompt, user_message, max_tokens=800, temperature=0.3):
    """
    Call AI API with system + user messages (chat format).
    Tries Groq first, then OpenRouter as fallback.
    """
    timeout = getattr(settings, 'OPENROUTER_TIMEOUT', 60)

    providers = []

    groq_key = getattr(settings, 'GROQ_API_KEY', '')
    if groq_key:
        providers.append({
            'name': 'Groq',
            'api_url': getattr(settings, 'GROQ_API_ENDPOINT', 'https://api.groq.com/openai/v1/chat/completions'),
            'api_key': groq_key,
            'model': getattr(settings, 'GROQ_MODEL', 'llama-3.1-8b-instant'),
            'headers_extra': {},
        })

    openrouter_key = getattr(settings, 'OPENROUTER_API_KEY', '')
    if openrouter_key:
        providers.append({
            'name': 'OpenRouter',
            'api_url': getattr(settings, 'OPENROUTER_API_ENDPOINT', 'https://openrouter.ai/api/v1/chat/completions'),
            'api_key': openrouter_key,
            'model': getattr(settings, 'OPENROUTER_MODEL', 'google/gemma-3-4b-it:free'),
            'headers_extra': {
                'HTTP-Referer': 'https://npdc.ncpor.gov.in',
                'X-Title': 'NPDC AI Search',
            },
        })

    if not providers:
        logger.warning("No AI API keys configured for chat")
        return None

    for provider in providers:
        try:
            headers = {
                'Authorization': f'Bearer {provider["api_key"]}',
                'Content-Type': 'application/json',
            }
            headers.update(provider.get('headers_extra', {}))

            payload = {
                'model': provider['model'],
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_message},
                ],
                'temperature': temperature,
                'max_tokens': max_tokens,
            }

            response = requests.post(provider['api_url'], headers=headers, json=payload, timeout=timeout)
            if response.status_code == 200:
                result = response.json()
                text = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                if text:
                    logger.info(f"AI Search answer generated via {provider['name']}")
                    return text
                logger.warning(f"{provider['name']} returned empty chat response, trying next...")
                continue
            elif response.status_code == 429:
                logger.warning(f"{provider['name']} rate limited (429), trying next provider...")
                continue
            else:
                logger.error(f"{provider['name']} chat API error: HTTP {response.status_code}")
                continue
        except requests.exceptions.Timeout:
            logger.error(f"{provider['name']} chat API timeout, trying next...")
            continue
        except Exception as e:
            logger.error(f"{provider['name']} chat API error: {e}, trying next...")
            continue

    logger.error("All AI providers failed for chat")
    return None


def ai_search_answer(query, filters=None, top_k=5):
    """
    AI Search: Full-text search + LLM answer generation.
    
    1. Use PostgreSQL FTS to find top K datasets matching the query.
    2. Apply any filters (expedition, category, date range).
    3. Serialize the top K records into a context string.
    4. Call LLM with system prompt + context + user question.
    5. Return {answer, datasets[]}.
    """
    from django.db.models import Q
    from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, TrigramSimilarity
    from data_submission.models import DatasetSubmission

    if not query or len(query.strip()) < 3:
        return None

    # Check cache
    cache_key = f"ai_answer:{hashlib.md5((query + str(filters)).encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    # ----- 1. Build base queryset -----
    qs = DatasetSubmission.objects.filter(status='published')

    # ----- 2. Apply filters -----
    if filters:
        if filters.get('expedition'):
            exp_list = filters['expedition'] if isinstance(filters['expedition'], list) else [filters['expedition']]
            qs = qs.filter(expedition_type__in=exp_list)
        if filters.get('category'):
            cat_list = filters['category'] if isinstance(filters['category'], list) else [filters['category']]
            qs = qs.filter(category__in=cat_list)
        if filters.get('start_date') and filters.get('end_date'):
            try:
                from datetime import datetime as dt
                start = dt.strptime(filters['start_date'], '%Y-%m-%d').date()
                end = dt.strptime(filters['end_date'], '%Y-%m-%d').date()
                qs = qs.filter(temporal_start_date__lte=end, temporal_end_date__gte=start)
            except (ValueError, TypeError):
                pass

    # ----- 3. FTS search -----
    # Parse query into search terms
    phrases = re.findall(r'"([^"]+)"', query)
    remaining = re.sub(r'"[^"]+', '', query).strip()
    words = remaining.split() if remaining else []
    search_terms = phrases + words

    results = []

    if search_terms:
        # Strategy A: PostgreSQL Full-Text Search
        try:
            search_string = ' & '.join(search_terms)
            search_query = SearchQuery(search_string, search_type='raw')
            search_vector = (
                SearchVector('title', weight='A') +
                SearchVector('abstract', weight='B') +
                SearchVector('keywords', weight='A') +
                SearchVector('project_name', weight='C')
            )

            fts_results = (
                qs.annotate(search_rank=SearchRank(search_vector, search_query))
                .filter(
                    Q(search_rank__gte=0.001) |
                    Q(title__icontains=search_terms[0]) |
                    Q(abstract__icontains=search_terms[0]) |
                    Q(keywords__icontains=search_terms[0])
                )
                .distinct()
                .order_by('-search_rank')[:top_k]
            )
            results = list(fts_results)
        except Exception as e:
            logger.error(f"FTS search failed: {e}")

    # Strategy B: Fallback to icontains if FTS returned nothing
    if not results:
        try:
            q_filter = Q()
            for term in (search_terms or [query]):
                q_filter |= (
                    Q(title__icontains=term) |
                    Q(abstract__icontains=term) |
                    Q(keywords__icontains=term) |
                    Q(project_name__icontains=term)
                )
            results = list(qs.filter(q_filter).distinct()[:top_k])
        except Exception as e:
            logger.error(f"Fallback search failed: {e}")

    # ----- 4. Serialize datasets -----
    datasets_list = []
    context_lines = []

    # Get the real total number of published datasets for count questions
    try:
        total_published_count = DatasetSubmission.objects.filter(status='published').count()
    except Exception:
        total_published_count = None

    for i, d in enumerate(results, 1):
        ds = {
            'id': d.metadata_id,
            'title': d.title,
            'abstract': d.abstract[:150],
            'keywords': d.keywords[:100] if d.keywords else '',
            'category': d.get_category_display(),
            'expedition_type': d.get_expedition_type_display(),
            'temporal_start': str(d.temporal_start_date),
            'temporal_end': str(d.temporal_end_date),
        }
        datasets_list.append(ds)

        # Compact context for LLM (fewer tokens)
        context_lines.append(
            f"{i}. [ID: {d.metadata_id}] {d.title}\n"
            f"   {ds['category']} | {ds['expedition_type']} | {ds['temporal_start']} to {ds['temporal_end']}\n"
            f"   {ds['abstract']}\n"
        )

    # ----- Count / metadata queries: answer directly, no dataset cards -----
    COUNT_KEYWORDS = ['how many', 'how much', 'total number', 'number of dataset', 'count of dataset']
    is_count_query = any(kw in query.lower() for kw in COUNT_KEYWORDS)

    if is_count_query and total_published_count is not None:
        return {
            'answer': f"The NPDC repository currently has {total_published_count} published dataset{'s' if total_published_count != 1 else ''}.",
            'datasets': [],
        }

    # Track if a typo correction was applied
    corrected_query_used = None

    if not datasets_list:
        # ----- Try typo correction / AI suggestions -----
        corrected_query = None
        suggestions = []
        try:
            available_kw = get_available_keywords()
            suggestion_result = get_ai_suggestions(query, available_kw)
            if suggestion_result and not suggestion_result.get('off_topic', False):
                corrected_query = suggestion_result.get('corrected_query', '')
                suggestions = suggestion_result.get('suggestions', [])

                # Re-search with the corrected query
                if corrected_query and corrected_query.lower() != query.lower():
                    corrected_phrases = re.findall(r'"([^"]+)"', corrected_query)
                    corrected_remaining = re.sub(r'"[^"]+', '', corrected_query).strip()
                    corrected_words = corrected_remaining.split() if corrected_remaining else []
                    corrected_terms = corrected_phrases + corrected_words

                    if corrected_terms:
                        try:
                            corrected_string = ' & '.join(corrected_terms)
                            corrected_sq = SearchQuery(corrected_string, search_type='raw')
                            corrected_sv = (
                                SearchVector('title', weight='A') +
                                SearchVector('abstract', weight='B') +
                                SearchVector('keywords', weight='A') +
                                SearchVector('project_name', weight='C')
                            )
                            corrected_results = list(
                                qs.annotate(search_rank=SearchRank(corrected_sv, corrected_sq))
                                .filter(
                                    Q(search_rank__gte=0.001) |
                                    Q(title__icontains=corrected_terms[0]) |
                                    Q(abstract__icontains=corrected_terms[0]) |
                                    Q(keywords__icontains=corrected_terms[0])
                                )
                                .distinct()
                                .order_by('-search_rank')[:top_k]
                            )
                            if corrected_results:
                                results = corrected_results
                                corrected_query_used = corrected_query
                        except Exception as e:
                            logger.error(f"Corrected query search failed: {e}")
        except Exception as e:
            logger.error(f"AI suggestion during search failed: {e}")

        # Still no results after correction attempt
        if not results:
            answer_text = f"I couldn't find any matching NPDC datasets for '{query}'."
            if corrected_query and corrected_query.lower() != query.lower():
                answer_text += f" Did you mean '{corrected_query}'?"
            elif suggestions:
                answer_text += " Try rephrasing or using different keywords."

            result = {
                'answer': answer_text,
                'datasets': [],
                'corrected_query': corrected_query if corrected_query and corrected_query.lower() != query.lower() else None,
                'suggestions': suggestions,
            }
            cache.set(cache_key, result, AI_CACHE_TIMEOUT)
            return result

        # Re-serialize datasets from corrected search results
        for i, d in enumerate(results, 1):
            ds = {
                'id': d.metadata_id,
                'title': d.title,
                'abstract': d.abstract[:150],
                'keywords': d.keywords[:100] if d.keywords else '',
                'category': d.get_category_display(),
                'expedition_type': d.get_expedition_type_display(),
                'temporal_start': str(d.temporal_start_date),
                'temporal_end': str(d.temporal_end_date),
            }
            datasets_list.append(ds)
            context_lines.append(
                f"{i}. [ID: {d.metadata_id}] {d.title}\n"
                f"   {ds['category']} | {ds['expedition_type']} | {ds['temporal_start']} to {ds['temporal_end']}\n"
                f"   {ds['abstract']}\n"
            )

    # ----- 5. Build prompt & call LLM -----
    context_str = "\n".join(context_lines)
    total_note = (
        f"\nNOTE: The NPDC repository contains {total_published_count} published datasets in total. "
        f"The context below shows the top {len(datasets_list)} most relevant matches for this query.\n"
    ) if total_published_count is not None else ""

    system_prompt = (
        "You are Penguin, NPDC's search assistant. "
        "You searched the database and found the datasets below.\n"
        "RULES:\n"
        "1. Use ONLY the datasets below. Cite by title and [ID: X].\n"
        "2. Do NOT fabricate data. No markdown (**, ##). Plain text only.\n"
        "3. If the query is unrelated to polar/cryosphere science, start with 'UNRELATED:'.\n"
        "4. If results don't match the question, say you couldn't find matching datasets.\n"
        "5. For total count questions, use the count from the NOTE.\n"
        "6. Format each result as a SINGLE bullet in this exact structure:\n"
        "   • Title [ID: X] - Category, Region, StartDate to EndDate\n"
        "     Brief 1-2 sentence summary of what the dataset contains.\n"
        "   Do NOT add extra sub-bullets or split metadata across multiple lines.\n"
        "7. Start with one short sentence like 'I found X datasets related to ...'\n"
        "8. Speak naturally — say 'I found' not 'based on the provided datasets'."
    )

    user_msg = (
        f"{total_note}"
        f"Q: {query}\n\n"
        f"SEARCH RESULTS ({len(datasets_list)} matches):\n"
        f"{context_str}\n"
        f"Answer naturally, citing dataset titles and IDs."
    )

    answer = _call_llm_chat(system_prompt, user_msg, max_tokens=700, temperature=0.3)

    if not answer:
        answer = (
            "I'm having trouble generating an AI answer right now. "
            "However, I found the datasets listed below that may be relevant to your query."
        )
    else:
        # Clean up any markdown that slipped through
        answer = re.sub(r'\*\*([^*]+)\*\*', r'\1', answer)
        answer = re.sub(r'#+\s*', '', answer)
        answer = answer.strip()

    # ----- 6. Detect unrelated queries -----
    # If the LLM explicitly flagged the query as unrelated, clear datasets.
    is_unrelated = answer.upper().startswith('UNRELATED:')
    if is_unrelated:
        answer = answer[len('UNRELATED:'):].strip()
        datasets_list = []
    else:
        # Safety net: catch common LLM phrasings that signal irrelevance
        unrelated_phrases = [
            'does not seem to be related',
            'not related to polar',
            'not relevant to polar',
            'outside the scope of npdc',
            'not about polar',
            'unrelated to polar',
            'unrelated to npdc',
        ]
        answer_lower = answer.lower()
        if any(phrase in answer_lower for phrase in unrelated_phrases):
            datasets_list = []

    result = {
        'answer': answer,
        'datasets': datasets_list,
    }
    if corrected_query_used:
        result['corrected_query'] = corrected_query_used

    # Cache for 5 minutes
    cache.set(cache_key, result, AI_CACHE_TIMEOUT)
    return result
