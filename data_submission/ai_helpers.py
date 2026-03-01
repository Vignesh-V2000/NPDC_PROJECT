"""
AI-powered helpers for NPDC Data Submission.
Uses the same OpenRouter/Groq provider chain as npdc_search.ai_search.
Provides 8 AI features for the dataset submission workflow:
1. Auto-Classify (Category + Topic + ISO Topic)
2. Smart Keywords Generator
3. Abstract Quality Checker
4. Spatial Coordinate Extractor
5. Smart Form Pre-fill (composition of 1-4)
6. Reviewer Assistant
7. AI Title Generator
8. AI Purpose Generator
"""
import json
import re
import hashlib
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Reuse the shared AI caller from search module
from npdc_search.ai_search import _call_openrouter

# ===================== CONSTANTS =====================

VALID_CATEGORIES = [
    ('agriculture', 'Agriculture'),
    ('atmosphere', 'Atmosphere'),
    ('biological_classification', 'Biological Classification'),
    ('biosphere', 'Biosphere'),
    ('climate_indicators', 'Climate Indicators'),
    ('cryosphere', 'Cryosphere'),
    ('human_dimensions', 'Human Dimensions'),
    ('land_surface', 'Land Surface'),
    ('oceans', 'Oceans'),
    ('paleoclimate', 'Paleoclimate'),
    ('solid_earth', 'Solid Earth'),
    ('spectral_engineering', 'Spectral/Engineering'),
    ('sun_earth_interactions', 'Sun-Earth Interactions'),
    ('terrestrial_hydrosphere', 'Terrestrial Hydrosphere'),
    ('marine_science', 'Marine Science'),
    ('terrestrial_science', 'Terrestrial Science'),
    ('wind_profiler_radar', 'Wind Profiler Radar'),
    ('geotectonic_studies', 'Geotectonic Studies'),
    ('audio_signals', 'Audio Signals'),
]

VALID_ISO_TOPICS = [
    ('climatologyMeteorologyAtmosphere', 'Climatology/Meteorology/Atmosphere'),
    ('oceans', 'Oceans'),
    ('environment', 'Environment'),
    ('geoscientificInformation', 'Geoscientific Information'),
    ('imageryBaseMapsEarthCover', 'Imagery/Base Maps/Earth Cover'),
    ('inlandWaters', 'Inland Waters'),
    ('location', 'Location'),
    ('boundaries', 'Boundaries'),
    ('biota', 'Biota'),
    ('economy', 'Economy'),
    ('elevation', 'Elevation'),
    ('farming', 'Farming'),
    ('health', 'Health'),
    ('intelligenceMilitary', 'Intelligence/Military'),
    ('society', 'Society'),
    ('structure', 'Structure'),
    ('transportation', 'Transportation'),
    ('utilitiesCommunication', 'Utilities/Communication'),
]

CATEGORY_TOPIC_MAP = {
    "agriculture": ["Agriculture", "Atmosphere", "Biological Classification", "Biosphere",
        "Climate Indicators", "Cryosphere", "Human Dimensions", "Land Surface",
        "Oceans", "Paleoclimate", "Solid Earth", "Spectral/Engineering",
        "Sun-Earth Interactions", "Terrestrial Hydrosphere", "Marine Science",
        "Terrestrial Science", "Wind Profiler Radar", "Geotectonic Studies", "Audio Signals"],
    "atmosphere": ["Aerosols", "Air Quality", "Altitude", "Atmospheric Chemistry",
        "Atmospheric Electricity", "Atmospheric Phenomena", "Atmospheric Pressure",
        "Atmospheric Radiation", "Atmospheric Temperature", "Atmospheric Water Vapor",
        "Atmospheric Winds", "Clouds", "Cryosphere", "Precipitation",
        "Wind Profiler Radar", "Atmospheric Ozone", "Ionosphere", "Global Electric Circuit"],
    "biological_classification": ["Animals/Invertebrates", "Animals/Vertebrates", "Bacteria/Archaea",
        "Cryosphere", "Fungi", "Plants", "Protists", "Viruses"],
    "biosphere": ["Aquatic Ecosystems", "Cryosphere", "Ecological Dynamics",
        "Terrestrial Ecosystems", "Vegetation", "Ocean/Lake Records"],
    "climate_indicators": ["Air Temperature Indices", "Cryosphere", "Drought/Precipitation Indices",
        "Humidity Indices", "Hydrologic/Ocean Indices", "Ocean/Sst Indices", "Teleconnections"],
    "cryosphere": ["Cryosphere", "Frozen Ground", "Glaciers/Ice Sheets", "Sea Ice", "Snow/Ice"],
    "human_dimensions": ["Attitudes/Preferences/Behavior", "Boundaries", "Cryosphere", "Economic Resources",
        "Environmental Impacts", "Habitat Conversion/Fragmentation", "Human Health",
        "Infrastructure", "Land Use/Land Cover", "Natural Hazards", "Population"],
    "land_surface": ["Cryosphere", "Erosion/Sedimentation", "Frozen Ground", "Geomorphology",
        "Land Temperature", "Land Use/Land Cover", "Landscape", "Soils",
        "Surface Radiative Properties", "Topography", "Neo-tectonics"],
    "oceans": ["Ocean/Lake Records", "Marine Biology", "Ocean Chemistry", "Hydrography",
        "Marine Environment Monitoring", "Ocean Acoustics", "Marine Sediments", "Aquatic Sciences",
        "Biogeochemistry", "Nutrients", "Chlorophyll A", "Paleoclimate Reconstructions",
        "Ice Core Records", "Land Records", "Cryosphere"],
    "paleoclimate": ["Cryosphere", "Geodetics/Gravity", "Geomagnetism", "Geomorphology",
        "Geothermal", "Natural Resources", "Rocks/Minerals", "Seismology",
        "Tectonics", "Volcanoes", "Geo-Chemistry", "Paleo"],
    "solid_earth": ["Cryosphere", "Gamma Ray", "Infrared Wavelengths", "Lidar", "Microwave",
        "Platform Characteristics", "Radar", "Radio Wave", "Sensor Characteristics",
        "Ultraviolet Wavelengths", "Visible Wavelengths", "X-Ray", "GPS",
        "Seismology", "Geomagnetism"],
    "spectral_engineering": ["Cryosphere", "Ionosphere/Magnetosphere Dynamics", "Solar Activity",
        "Solar Energetic Particle Flux", "Solar Energetic Particle Properties"],
    "sun_earth_interactions": ["Cryosphere", "Glaciers/Ice Sheets", "Ground Water", "Snow/Ice",
        "Surface Water", "Water Quality/Water Chemistry", "Polar Ionosphere"],
    "terrestrial_hydrosphere": ["Cryosphere"],
    "marine_science": ["Aquatic Sciences", "Bathymetry/Seafloor Topography", "Coastal Processes",
        "Cryosphere", "Marine Environment Monitoring", "Marine Geophysics",
        "Marine Sediments", "Marine Volcanism", "Ocean Acoustics", "Ocean Chemistry",
        "Ocean Circulation", "Ocean Heat Budget", "Ocean Optics", "Ocean Pressure",
        "Ocean Temperature", "Ocean Waves", "Ocean Winds", "Salinity/Density",
        "Sea Ice", "Sea Surface Topography", "Tides", "Water Quality", "Earth Science Test"],
    "terrestrial_science": ["Cryosphere"],
    "wind_profiler_radar": ["Atmospheric Science"],
    "geotectonic_studies": ["Surveying & Mapping"],
    "audio_signals": ["Physical data"],
}

# Default spatial bounding boxes for expedition types
EXPEDITION_SPATIAL_DEFAULTS = {
    "antarctic": {"north": -60.0, "south": -90.0, "east": 180.0, "west": -180.0},
    "arctic": {"north": 90.0, "south": 60.0, "east": 180.0, "west": -180.0},
    "southern_ocean": {"north": -40.0, "south": -78.0, "east": 180.0, "west": -180.0},
    "himalaya": {"north": 36.0, "south": 26.0, "east": 105.0, "west": 73.0},
}

AI_CACHE_TIMEOUT = 86400  # 24 hours

# Per-user AI rate limit: max requests per window
AI_RATE_LIMIT_MAX = 30
AI_RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds


def check_ai_rate_limit(user_id):
    """
    Check per-user AI rate limit (30 requests per hour).
    Returns True if the request is allowed, False if the limit has been reached.
    """
    cache_key = f"ai_rate_limit:{user_id}"
    count = cache.get(cache_key, 0)
    if count >= AI_RATE_LIMIT_MAX:
        return False
    # Increment counter; set TTL only on first call so the window is fixed
    if count == 0:
        cache.set(cache_key, 1, AI_RATE_LIMIT_WINDOW)
    else:
        cache.set(cache_key, count + 1, AI_RATE_LIMIT_WINDOW)
    return True


def _safe_json_parse(text):
    """Extract and parse JSON from AI response text."""
    if not text:
        return None
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try to extract JSON from markdown code blocks
    patterns = [
        r'```json\s*([\s\S]*?)\s*```',
        r'```\s*([\s\S]*?)\s*```',
        r'\{[\s\S]*\}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return json.loads(match.group(1) if '```' in pattern else match.group(0))
            except (json.JSONDecodeError, IndexError):
                continue
    return None


# =====================================================================
# FEATURE 7: AI Title Generator
# =====================================================================

def generate_title(abstract, expedition_type=""):
    """
    AI-powered dataset title generator.
    Generates a concise, descriptive title (max 220 chars) from the abstract.
    Returns dict with 'title' and 'alternatives' keys.
    """
    if not abstract or len(abstract.strip()) < 20:
        return {"title": "", "alternatives": [], "error": "Abstract is too short to generate a title."}

    cache_key = f"ai_gen_title:{hashlib.md5(f'{abstract[:200]}:{expedition_type}'.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    expedition_label = {
        "antarctic": "Antarctic",
        "arctic": "Arctic",
        "southern_ocean": "Southern Ocean",
        "himalaya": "Himalayan",
    }.get(expedition_type, "Polar")

    _abstract_trunc = abstract[:1500]
    prompt = f"""You are a scientific metadata expert for the National Polar Data Center (NPDC).
Generate a concise, descriptive dataset title from the given abstract.

ABSTRACT: {_abstract_trunc}
EXPEDITION TYPE: {expedition_type}

Requirements:
- Title must be UNDER 220 characters
- Include the expedition/region name (e.g., "{expedition_label}")
- Include the type of data or measurement (e.g., "Temperature Records", "Bathymetric Survey", "Ice Core Analysis")
- Include the specific location if mentioned in the abstract
- Follow academic dataset naming conventions
- Do NOT start with "Dataset" or "Data"
- Be specific rather than generic

Also provide 2 alternative titles for the user to choose from.

Respond with ONLY valid JSON:
{{"title": "<primary title>", "alternatives": ["<alt title 1>", "<alt title 2>"]}}"""

    response = _call_openrouter(prompt, max_tokens=300, temperature=0.5)
    result = _safe_json_parse(response)

    if result and result.get('title'):
        # Ensure title length constraint
        result['title'] = str(result['title']).strip()[:220]
        result['alternatives'] = [str(a).strip()[:220] for a in result.get('alternatives', [])][:2]
        cache.set(cache_key, result, AI_CACHE_TIMEOUT)
        return result

    return {"title": "", "alternatives": [], "error": "Could not generate a title."}


# =====================================================================
# FEATURE 8: AI Purpose Generator
# =====================================================================

def generate_purpose(title, abstract, expedition_type=""):
    """
    AI-powered purpose statement generator.
    Generates a purpose/rationale (max 1000 chars) that complements the abstract.
    Returns dict with 'purpose' key.
    """
    if not abstract or len(abstract.strip()) < 20:
        return {"purpose": "", "error": "Abstract is too short to generate a purpose."}

    cache_key = f"ai_gen_purpose:{hashlib.md5(f'{title}:{abstract[:200]}:{expedition_type}'.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    _abstract_trunc = abstract[:1500]
    prompt = f"""You are a scientific metadata expert for the National Polar Data Center (NPDC).
Generate a PURPOSE statement for a polar research dataset. The purpose should explain WHY the data was collected.

TITLE: {title}
ABSTRACT: {_abstract_trunc}
EXPEDITION TYPE: {expedition_type}

Requirements:
- The purpose MUST be DIFFERENT from the abstract — do NOT repeat the abstract
- Focus on the scientific RATIONALE and MOTIVATION for collecting this data
- Explain how the data contributes to broader research goals
- Mention the intended use or application of the dataset
- Keep it under 1000 characters
- Write in formal scientific language
- Start with phrases like "This dataset was collected to...", "The purpose of this data collection is to...", or "This dataset supports..."

Respond with ONLY valid JSON:
{{"purpose": "<purpose statement>"}}"""

    response = _call_openrouter(prompt, max_tokens=400, temperature=0.4)
    result = _safe_json_parse(response)

    if result and result.get('purpose'):
        result['purpose'] = str(result['purpose']).strip()[:1000]
        cache.set(cache_key, result, AI_CACHE_TIMEOUT)
        return result

    return {"purpose": "", "error": "Could not generate a purpose statement."}


# =====================================================================
# FEATURE 1: Auto-Classify (Category + Topic + ISO Topic)
# =====================================================================

def classify_dataset(title, abstract, expedition_type=""):
    """
    AI-powered classification of dataset into category, topic, and ISO topic.
    Returns dict with 'category', 'topic', 'iso_topic' keys.
    """
    cache_key = f"ai_classify:{hashlib.md5(f'{title}:{abstract[:100]}:{expedition_type}'.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    category_keys = ", ".join([k for k, _ in VALID_CATEGORIES])
    iso_keys = ", ".join([k for k, _ in VALID_ISO_TOPICS])
    _abstract_trunc = abstract[:1000]

    prompt = f"""You are a scientific data classification expert for the National Polar Data Center (NPDC).
Given a dataset title and abstract, classify it into the correct category, topic, and ISO topic.

DATASET TITLE: {title}
DATASET ABSTRACT: {_abstract_trunc}
EXPEDITION TYPE: {expedition_type}

AVAILABLE CATEGORIES (use the exact key):
{category_keys}

AVAILABLE ISO TOPICS (use the exact key):
{iso_keys}

For the "topic" field, pick the most relevant scientific sub-topic based on the category.

Respond with ONLY valid JSON (no explanation):
{{"category": "<category_key>", "topic": "<topic_name>", "iso_topic": "<iso_topic_key>"}}"""

    response = _call_openrouter(prompt, max_tokens=200, temperature=0.2)
    result = _safe_json_parse(response)

    if result:
        # Validate category
        valid_cat_keys = [k for k, _ in VALID_CATEGORIES]
        if result.get('category') not in valid_cat_keys:
            result['category'] = 'cryosphere'  # safe default for polar data

        # Validate topic against the category
        cat = result.get('category', '')
        valid_topics = CATEGORY_TOPIC_MAP.get(cat, [])
        if result.get('topic') not in valid_topics and valid_topics:
            result['topic'] = valid_topics[0]

        # Validate ISO topic
        valid_iso_keys = [k for k, _ in VALID_ISO_TOPICS]
        if result.get('iso_topic') not in valid_iso_keys:
            result['iso_topic'] = 'environment'  # safe default

        cache.set(cache_key, result, AI_CACHE_TIMEOUT)
        return result

    return {"category": "", "topic": "", "iso_topic": ""}


# =====================================================================
# FEATURE 2: Smart Keywords Generator
# =====================================================================

def suggest_keywords(title, abstract, category="", num_keywords=10):
    """
    AI-powered GCMD-aligned keyword generator.
    Returns list of keyword strings.
    """
    cache_key = f"ai_keywords:{hashlib.md5(f'{title}:{abstract[:100]}:{category}'.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    _abstract_trunc = abstract[:1000]
    prompt = f"""You are a scientific metadata expert for the National Polar Data Center.
Generate {num_keywords} relevant GCMD-compatible scientific keywords for this polar research dataset.

TITLE: {title}
ABSTRACT: {_abstract_trunc}
CATEGORY: {category}

Requirements:
- Keywords should be relevant to polar/cryosphere science
- Include broader terms (e.g. "Glaciology") and specific terms (e.g. "Ice Core Analysis")
- Follow Global Change Master Directory (GCMD) keyword conventions
- Include geographic terms if applicable (e.g. "Antarctica", "Arctic Ocean")

Respond with ONLY a JSON array of keyword strings:
["keyword1", "keyword2", "keyword3", ...]"""

    response = _call_openrouter(prompt, max_tokens=300, temperature=0.4)
    result = _safe_json_parse(response)

    if isinstance(result, list):
        # Ensure all items are strings
        keywords = [str(k).strip() for k in result if k][:num_keywords]
        cache.set(cache_key, keywords, AI_CACHE_TIMEOUT)
        return keywords

    return []


# =====================================================================
# FEATURE 3: Abstract Quality Checker
# =====================================================================

def check_abstract_quality(title, abstract, expedition_type=""):
    """
    AI-powered abstract quality assessment.
    Returns dict with 'score' (0-100), 'grade', and 'suggestions' list.
    """
    if not abstract or len(abstract.strip()) < 10:
        return {
            "score": 0,
            "grade": "poor",
            "suggestions": ["Abstract is too short. Please provide a meaningful description of your dataset."]
        }

    cache_key = f"ai_abstract_q:{hashlib.md5(f'{title}:{abstract[:200]}'.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    _abstract_trunc = abstract[:1500]
    prompt = f"""You are a scientific writing reviewer for the National Polar Data Center.
Evaluate the quality of this dataset abstract for a polar research data repository.

TITLE: {title}
ABSTRACT: {_abstract_trunc}
EXPEDITION TYPE: {expedition_type}

Score the abstract 0-100 based on these criteria:
1. COMPLETENESS - Does it mention: location, time period, methodology, key variables measured?
2. CLARITY - Is it clear and well-written?
3. SCIENTIFIC RIGOR - Does it use appropriate scientific terminology?
4. LENGTH - Is it adequate (ideally 150-800 characters)?
5. SPECIFICITY - Does it provide specific details, not just generic statements?

Respond with ONLY valid JSON:
{{"score": <0-100>, "grade": "<excellent|good|fair|poor>", "suggestions": ["suggestion1", "suggestion2"]}}

Keep suggestions to 2-4 concise, actionable items. If the abstract is excellent, provide 1 positive note."""

    response = _call_openrouter(prompt, max_tokens=300, temperature=0.3)
    result = _safe_json_parse(response)

    if result and isinstance(result.get('score'), (int, float)):
        result['score'] = max(0, min(100, int(result['score'])))
        if 'grade' not in result:
            if result['score'] >= 80:
                result['grade'] = 'excellent'
            elif result['score'] >= 60:
                result['grade'] = 'good'
            elif result['score'] >= 40:
                result['grade'] = 'fair'
            else:
                result['grade'] = 'poor'
        result['suggestions'] = result.get('suggestions', [])[:4]
        cache.set(cache_key, result, AI_CACHE_TIMEOUT)
        return result

    return {"score": 50, "grade": "fair", "suggestions": ["Could not fully analyze the abstract."]}


# =====================================================================
# FEATURE 4: Spatial Coordinate Extractor
# =====================================================================

def extract_spatial_data(title, abstract, expedition_type=""):
    """
    AI-powered spatial coordinate extraction.
    Returns dict with north, south, east, west coordinates + zone_type.
    """
    cache_key = f"ai_spatial:{hashlib.md5(f'{title}:{abstract[:100]}:{expedition_type}'.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Start with expedition defaults
    defaults = EXPEDITION_SPATIAL_DEFAULTS.get(expedition_type, {
        "north": 90.0, "south": -90.0, "east": 180.0, "west": -180.0
    })

    prompt = f"""You are a geographic metadata expert for the National Polar Data Center.
Extract or estimate the geographic bounding box coordinates for this polar research dataset.

TITLE: {title}
ABSTRACT: {abstract[:1000]}
EXPEDITION TYPE: {expedition_type}

DEFAULT BOUNDING BOX for this expedition type:
North: {defaults['north']}, South: {defaults['south']}, East: {defaults['east']}, West: {defaults['west']}

Instructions:
- If the abstract mentions specific locations (e.g. "Maitri Station", "Larsemann Hills", "Schirmacher Oasis", "Svalbard"), 
  provide coordinates specific to that location as a bounding box.
- If the abstract mentions a broad region (e.g. "East Antarctica", "Indian Ocean sector"), provide a regional bounding box.
- If no specific location is mentioned, use the default bounding box for the expedition type.
- Determine if this is "bounding_box", "global", or "point" data.
- Also suggest a specific "subregion" name if found (e.g. "Schirmacher Oasis").

Well-known polar research locations:
- Maitri Station: lat ~-70.77, lon ~11.73
- Bharati Station: lat ~-69.41, lon ~76.19
- Larsemann Hills: lat ~-69.4, lon ~76.2
- Schirmacher Oasis: lat ~-70.75, lon ~11.72
- Himadri Station (Svalbard): lat ~78.92, lon ~11.93
- IndARC mooring: lat ~79.0, lon ~12.0

Respond with ONLY valid JSON:
{{"north": <float>, "south": <float>, "east": <float>, "west": <float>, "zone_type": "<bounding_box|global|point>", "location_name": "<detected location or empty string>", "subregion": "<specific subregion name e.g. Larsemann Hills>"}}"""

    response = _call_openrouter(prompt, max_tokens=250, temperature=0.2)
    result = _safe_json_parse(response)

    # Robust processing: Ensure result is a dict and has valid values
    final_result = defaults.copy()
    final_result['zone_type'] = 'bounding_box'
    final_result['location_name'] = ''
    final_result['subregion'] = ''

    if result and isinstance(result, dict):
        try:
            # Update only valid coordinates
            if 'north' in result: final_result['north'] = max(-90, min(90, float(result['north'])))
            if 'south' in result: final_result['south'] = max(-90, min(90, float(result['south'])))
            if 'east' in result: final_result['east'] = max(-180, min(180, float(result['east'])))
            if 'west' in result: final_result['west'] = max(-180, min(180, float(result['west'])))
            
            # Ensure north >= south
            if final_result['north'] < final_result['south']:
                final_result['north'], final_result['south'] = final_result['south'], final_result['north']

            final_result['zone_type'] = result.get('zone_type', 'bounding_box')
            final_result['location_name'] = result.get('location_name', '')
            final_result['subregion'] = result.get('subregion', '')
        except (ValueError, TypeError):
            # Keep defaults on error
            pass
    
    # Store in cache
    cache.set(cache_key, final_result, AI_CACHE_TIMEOUT)
    return final_result


def prefill_form(title, abstract, expedition_type=""):
    """
    AI-powered form pre-fill using a single unified prompt.
    Combines classification, keywords, abstract quality, and spatial extraction
    into one API call to minimize token usage and latency.
    Returns a comprehensive dict with all suggested field values.
    """
    # Check combined cache first
    combined_cache_key = f"ai_prefill:{hashlib.md5(f'{title}:{abstract[:200]}:{expedition_type}'.encode()).hexdigest()}"
    cached = cache.get(combined_cache_key)
    if cached:
        return cached

    result = {
        "classification": {},
        "keywords": [],
        "abstract_quality": {},
        "spatial": {},
        "location": {},
    }

    defaults = EXPEDITION_SPATIAL_DEFAULTS.get(expedition_type, {
        "north": 90.0, "south": -90.0, "east": 180.0, "west": -180.0
    })
    category_keys = ", ".join([k for k, _ in VALID_CATEGORIES])
    iso_keys = ", ".join([k for k, _ in VALID_ISO_TOPICS])
    _abstract_trunc = abstract[:1500]

    prompt = f"""You are a scientific metadata expert for the National Polar Data Center (NPDC).
Given the following polar research dataset, perform ALL four tasks below in a single JSON response.

TITLE: {title}
ABSTRACT: {_abstract_trunc}
EXPEDITION TYPE: {expedition_type}
DEFAULT BOUNDING BOX: N={defaults['north']}, S={defaults['south']}, E={defaults['east']}, W={defaults['west']}

TASK 1 — CLASSIFICATION
Pick one category key and one ISO topic key from the lists below, and choose the most relevant topic name.
Categories: {category_keys}
ISO Topics: {iso_keys}

TASK 2 — KEYWORDS
Generate 10 GCMD-compatible scientific keywords (array of strings).

TASK 3 — ABSTRACT QUALITY
Score 0–100 for completeness, clarity, scientific rigor, length, and specificity.
Grade: excellent (>=80), good (>=60), fair (>=40), poor (<40).
Provide 2–4 concise, actionable suggestions.

TASK 4 — SPATIAL BOUNDING BOX
Extract or estimate the geographic bounding box. Use the default if no location is found.
Known locations: Maitri Station (~-70.77,11.73), Bharati Station (~-69.41,76.19),
Larsemann Hills (~-69.4,76.2), Schirmacher Oasis (~-70.75,11.72), Himadri/Svalbard (~78.92,11.93).
zone_type: "bounding_box", "global", or "point".

Respond with ONLY valid JSON:
{{"classification": {{"category": "<key>", "topic": "<topic_name>", "iso_topic": "<key>"}},
  "keywords": ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6", "kw7", "kw8", "kw9", "kw10"],
  "abstract_quality": {{"score": <0-100>, "grade": "<excellent|good|fair|poor>", "suggestions": ["...", "..."]}},
  "spatial": {{"north": <float>, "south": <float>, "east": <float>, "west": <float>, "zone_type": "<type>", "location_name": "<str>", "subregion": "<str>"}}}}"""

    ai_response = _call_openrouter(prompt, max_tokens=800, temperature=0.3)
    combined = _safe_json_parse(ai_response)

    if combined and isinstance(combined, dict):
        # --- Process classification ---
        clf = combined.get("classification", {})
        valid_cat_keys = [k for k, _ in VALID_CATEGORIES]
        if clf.get('category') not in valid_cat_keys:
            clf['category'] = 'cryosphere'
        cat = clf.get('category', '')
        valid_topics = CATEGORY_TOPIC_MAP.get(cat, [])
        if clf.get('topic') not in valid_topics and valid_topics:
            clf['topic'] = valid_topics[0]
        valid_iso_keys = [k for k, _ in VALID_ISO_TOPICS]
        if clf.get('iso_topic') not in valid_iso_keys:
            clf['iso_topic'] = 'environment'
        result["classification"] = clf

        # --- Process keywords ---
        kws = combined.get("keywords", [])
        if isinstance(kws, list):
            result["keywords"] = [str(k).strip() for k in kws if k][:10]

        # --- Process abstract quality ---
        aq = combined.get("abstract_quality", {})
        if isinstance(aq.get("score"), (int, float)):
            aq["score"] = max(0, min(100, int(aq["score"])))
        if "grade" not in aq:
            s = aq.get("score", 0)
            aq["grade"] = "excellent" if s >= 80 else "good" if s >= 60 else "fair" if s >= 40 else "poor"
        aq["suggestions"] = aq.get("suggestions", [])[:4]
        result["abstract_quality"] = aq

        # --- Process spatial ---
        spatial_raw = combined.get("spatial", {})
        final_spatial = defaults.copy()
        final_spatial['zone_type'] = 'bounding_box'
        final_spatial['location_name'] = ''
        final_spatial['subregion'] = ''
        if isinstance(spatial_raw, dict):
            try:
                if 'north' in spatial_raw: final_spatial['north'] = max(-90, min(90, float(spatial_raw['north'])))
                if 'south' in spatial_raw: final_spatial['south'] = max(-90, min(90, float(spatial_raw['south'])))
                if 'east' in spatial_raw: final_spatial['east'] = max(-180, min(180, float(spatial_raw['east'])))
                if 'west' in spatial_raw: final_spatial['west'] = max(-180, min(180, float(spatial_raw['west'])))
                if final_spatial['north'] < final_spatial['south']:
                    final_spatial['north'], final_spatial['south'] = final_spatial['south'], final_spatial['north']
                final_spatial['zone_type'] = spatial_raw.get('zone_type', 'bounding_box')
                final_spatial['location_name'] = spatial_raw.get('location_name', '')
                final_spatial['subregion'] = spatial_raw.get('subregion', '')
            except (ValueError, TypeError):
                pass
        result["spatial"] = final_spatial

    else:
        # Fallback to individual calls if combined response fails
        logger.warning("Combined prefill AI call failed, falling back to individual calls.")
        try:
            result["classification"] = classify_dataset(title, abstract, expedition_type)
        except Exception as e:
            logger.error(f"AI classify error in prefill: {e}")
            result["classification"] = {"category": "", "topic": "", "iso_topic": ""}

        try:
            category = result["classification"].get("category", "")
            result["keywords"] = suggest_keywords(title, abstract, category)
        except Exception as e:
            logger.error(f"AI keywords error in prefill: {e}")
            result["keywords"] = []

        try:
            result["abstract_quality"] = check_abstract_quality(title, abstract, expedition_type)
        except Exception as e:
            logger.error(f"AI abstract quality error in prefill: {e}")
            result["abstract_quality"] = {"score": 0, "grade": "unknown", "suggestions": []}

        try:
            result["spatial"] = extract_spatial_data(title, abstract, expedition_type)
        except Exception as e:
            logger.error(f"AI spatial error in prefill: {e}")
            result["spatial"] = EXPEDITION_SPATIAL_DEFAULTS.get(expedition_type, {}).copy()

    # Derive location details from expedition type + spatial subregion
    try:
        exp_map = {
            "antarctic": ("region", "Antarctica"),
            "arctic": ("region", "Arctic"),
            "southern_ocean": ("ocean", "Southern Ocean"),
            "himalaya": ("region", "Himalaya"),
        }
        loc_cat, loc_type = exp_map.get((expedition_type or "").lower(), ("", ""))
        result["location"] = {
            "category": loc_cat,
            "type": loc_type,
            "subregion": result["spatial"].get("subregion", "")
        }
    except Exception as e:
        logger.error(f"AI location logic error: {e}")
        result["location"] = {"category": "", "type": "", "subregion": ""}

    cache.set(combined_cache_key, result, AI_CACHE_TIMEOUT)
    return result


# =====================================================================
# FEATURE 6: AI Reviewer Assistant
# =====================================================================

def generate_review_notes(submission_data):
    """
    AI-powered reviewer notes generator.
    submission_data: dict with title, abstract, expedition_type, category, keywords,
                     spatial bounds, temporal dates, etc.
    Returns dict with 'completeness_score', 'issues', 'suggestions', 'draft_notes'.
    """
    cache_key = f"ai_review:{hashlib.md5(str(submission_data.get('id', '')).encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    prompt = f"""You are a senior dataset reviewer for the National Polar Data Center (NPDC).
Evaluate this dataset submission for quality, completeness, and consistency.

SUBMISSION DATA:
- Title: {submission_data.get('title', 'N/A')}
- Abstract: {submission_data.get('abstract', 'N/A')}
- Expedition Type: {submission_data.get('expedition_type', 'N/A')}
- Category: {submission_data.get('category', 'N/A')}
- ISO Topic: {submission_data.get('iso_topic', 'N/A')}
- Keywords: {submission_data.get('keywords', 'N/A')}
- Temporal Coverage: {submission_data.get('temporal_start', 'N/A')} to {submission_data.get('temporal_end', 'N/A')}
- Spatial Bounds: N:{submission_data.get('north_lat', 'N/A')}, S:{submission_data.get('south_lat', 'N/A')}, E:{submission_data.get('east_lon', 'N/A')}, W:{submission_data.get('west_lon', 'N/A')}
- Purpose: {submission_data.get('purpose', 'N/A')}
- Data Set Progress: {submission_data.get('progress', 'N/A')}
- Has Data File: {submission_data.get('has_file', False)}

Check for:
1. COMPLETENESS - Are all important fields filled? Is abstract adequate?
2. CONSISTENCY - Does expedition type match spatial coordinates? Does category match abstract content?
3. QUALITY - Are keywords relevant? Is the title descriptive? Temporal dates make sense?
4. ISSUES - Any red flags (e.g., future dates, impossible coordinates, mismatch between fields)?

Respond with ONLY valid JSON:
{{
    "completeness_score": <0-100>,
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1", "suggestion2"],
    "draft_notes": "<2-3 sentence reviewer notes suitable for pasting into review form>"
}}"""

    response = _call_openrouter(prompt, max_tokens=500, temperature=0.3)
    result = _safe_json_parse(response)

    if result:
        result['completeness_score'] = max(0, min(100, int(result.get('completeness_score', 50))))
        result['issues'] = result.get('issues', [])[:6]
        result['suggestions'] = result.get('suggestions', [])[:6]
        result['draft_notes'] = result.get('draft_notes', '')
        cache.set(cache_key, result, AI_CACHE_TIMEOUT)
        return result

    return {
        "completeness_score": 0,
        "issues": ["AI analysis unavailable"],
        "suggestions": [],
        "draft_notes": ""
    }


# =====================================================================
# FEATURE 9: AI Data Resolution Suggester
# =====================================================================

def suggest_resolution(title, abstract, expedition_type=""):
    """
    AI-powered data resolution suggester.
    Suggests latitude/longitude resolution (DMS), horizontal/vertical resolution ranges,
    and temporal resolution based on dataset context.
    Returns dict with resolution fields.
    """
    if not abstract or len(abstract.strip()) < 20:
        return {"error": "Abstract is too short to suggest resolution."}

    cache_key = f"ai_resolution:{hashlib.md5(f'{title}:{abstract[:200]}:{expedition_type}'.encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    expedition_label = {
        "antarctic": "Antarctic",
        "arctic": "Arctic",
        "southern_ocean": "Southern Ocean",
        "himalaya": "Himalayan",
    }.get(expedition_type, "Polar")

    _abstract_trunc = abstract[:1500]
    prompt = f"""You are a scientific metadata expert for the National Polar Data Center (NPDC).
Based on the dataset title, abstract, and expedition type, suggest appropriate data resolution values.

TITLE: {title}
ABSTRACT: {_abstract_trunc}
EXPEDITION TYPE: {expedition_label}

IMPORTANT: Think carefully about the TYPE of dataset:
- Ice cores, sediment cores, paleoclimate records → temporal resolution is typically "Annually" or "Multi-annual" (NOT sub-daily/hourly!)
- Real-time sensors, weather stations, buoys → temporal resolution is typically "Hourly", "Sub-daily", or "Daily"
- Satellite/remote sensing → temporal resolution depends on revisit time ("Daily", "Weekly", "Monthly")
- Field surveys, one-time expeditions → temporal resolution is "One-time"
- Bathymetric/topographic surveys → temporal resolution is "One-time", spatial focus

Resolution guidelines for polar/environmental datasets:
- Latitude/Longitude Resolution: expressed in Degrees, Minutes, Seconds (integers)
  - Satellite data: typically 0 deg 0 min 1-30 sec
  - Field measurements / ice cores: typically 0 deg 0 min 1-5 sec
  - Regional surveys: typically 0 deg 1-30 min 0 sec
  - Large-scale models: typically 1-5 deg 0 min 0 sec
- Horizontal Resolution Range: one of "Point Resolution", "< 1 meter", "1 meter - 30 meters", "30 meters - 100 meters", "100 meters - 250 meters", "250 meters - 500 meters", "500 meters - 1 km", "1 km - 10 km", "10 km - 50 km", "50 km - 100 km", "100 km - 250 km", "250 km - 500 km", "500 km - 1000 km", "> 1000 km", "Varies"
- Vertical Resolution: a descriptive string like "1 centimeter", "1 meter", "10 meters", "Point", "Not Applicable"
- Vertical Resolution Range: one of "Point Resolution", "< 1 meter", "1 meter - 100 meters", "> 100 meters", "Not Applicable", "Varies"
- Temporal Resolution: a descriptive string like "Hourly", "Daily", "Weekly", "Monthly", "Annually", "Multi-annual", "Sub-daily", "One-time"
- Temporal Resolution Range: one of "Hourly - Sub-hourly", "Sub-daily", "Daily", "Weekly", "Monthly", "Annually", "Sub-annual", "Multi-annual", "One-time", "Varies"

Respond with ONLY valid JSON:
{{
    "lat_deg": "<integer degrees>",
    "lat_min": "<integer minutes>",
    "lat_sec": "<integer seconds>",
    "lon_deg": "<integer degrees>",
    "lon_min": "<integer minutes>",
    "lon_sec": "<integer seconds>",
    "horizontal_resolution_range": "<one of the listed options>",
    "vertical_resolution": "<descriptive string>",
    "vertical_resolution_range": "<one of the listed options>",
    "temporal_resolution": "<descriptive string>",
    "temporal_resolution_range": "<one of the listed options>"
}}"""

    response = _call_openrouter(prompt, max_tokens=400, temperature=0.3)
    result = _safe_json_parse(response)

    if result:
        # Sanitize numeric DMS fields to integers
        for key in ('lat_deg', 'lat_min', 'lat_sec', 'lon_deg', 'lon_min', 'lon_sec'):
            try:
                result[key] = str(int(str(result.get(key, '0')).strip()))
            except (ValueError, TypeError):
                result[key] = '0'

        # Sanitize string fields
        for key in ('horizontal_resolution_range', 'vertical_resolution',
                     'vertical_resolution_range', 'temporal_resolution', 'temporal_resolution_range'):
            result[key] = str(result.get(key, '')).strip()[:50]

        cache.set(cache_key, result, AI_CACHE_TIMEOUT)
        return result

    return {"error": "Could not suggest resolution values."}
