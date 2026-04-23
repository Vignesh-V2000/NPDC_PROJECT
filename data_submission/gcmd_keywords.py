"""GCMD keyword guidance used by NPDC AI keyword generation."""

GCMD_KEYWORD_HIERARCHY = {
    "Atmosphere": {
        "Atmospheric Chemistry": [
            "Aerosols",
            "Atmospheric Constituents",
            "Atmospheric Ozone",
            "Trace Gases",
            "Volcanic Emissions",
            "Black Carbon",
        ],
        "Atmospheric Temperature": [
            "Air Temperature Observations",
            "Temperature Profiles",
            "Surface Temperature",
        ],
        "Atmospheric Winds": [
            "Wind Speed",
            "Wind Direction",
            "Jet Streams",
        ],
        "Clouds": [
            "Cloud Microphysics",
            "Cloud Cover",
            "Cloud Height",
        ],
        "Precipitation": [
            "Precipitation Amount",
            "Rain Gauges",
            "Snow Water Equivalent",
        ],
        "Atmospheric Radiation": [
            "Solar Radiation",
            "UV Radiation",
            "Infrared Radiation",
        ],
    },
    "Oceans": {
        "Ocean Chemistry": [
            "Salinity/Density",
            "Nutrients",
            "Dissolved Oxygen",
            "Ocean Acidification",
        ],
        "Oceanography": [
            "Sea Surface Temperature",
            "Ocean Circulation",
            "Ocean Heat Budget",
            "Sea Surface Topography",
        ],
        "Marine Biology": [
            "Phytoplankton",
            "Zooplankton",
            "Marine Mammal Observations",
        ],
        "Sea Ice": [
            "Sea Ice Concentration",
            "Sea Ice Thickness",
            "Sea Ice Type",
        ],
        "Bathymetry/Seafloor Topography": [
            "Multibeam Bathymetry",
            "Seafloor Mapping",
        ],
    },
    "Biosphere": {
        "Aquatic Ecosystems": [
            "Freshwater Ecosystems",
            "Marine Ecosystems",
            "Wetlands",
        ],
        "Terrestrial Ecosystems": [
            "Vegetation",
            "Soil Moisture",
            "Land Cover",
        ],
    },
    "Cryosphere": {
        "Glaciers/Ice Sheets": [
            "Glacier Mass Balance",
            "Ice Core Records",
            "Ice Sheet Dynamics",
        ],
        "Snow/Ice": [
            "Snow Depth",
            "Snow Density",
            "Permafrost",
        ],
        "Frozen Ground": [
            "Permafrost Temperature",
            "Frozen Ground Monitoring",
        ],
        "Paleoclimate": [
            "Paleoclimate Reconstructions",
            "Palaeoenvironmental",
            "Climatic History",
            "Multiproxy Analyses",
            "Environmental Variability",
        ],
    },
    "Geoscientific Information": {
        "Geomorphology": [
            "Glacial Geomorphology",
            "Sediment Transport",
            "Depositional Processes",
        ],
        "Seismology": [
            "Earthquake Monitoring",
        ],
        "Geodesy": [
            "GPS", "Geodetic Surveying",
        ],
        "Marine Sediments": [
            "Sediment Cores",
            "Submarine Geology",
        ],
        "Lacustrine Sediments": [
            "Lake Sediments",
            "Depositional Records",
        ],
    },
    "Location": {
        "Polar Regions": [
            "Antarctica",
            "East Antarctica",
            "Arctic Ocean",
            "Southern Ocean",
            "Himalaya",
        ],
        "Antarctic Locations": [
            "Larsemann Hills",
        ],
    },
}


def normalize_keyword(keyword):
    return " ".join(str(keyword or "").strip().lower().split())


def flatten_gcmd_keywords(hierarchy):
    """Flatten the hierarchy to get ALL keywords at all levels."""
    keywords = []
    for parent, children in hierarchy.items():
        keywords.append(parent)
        if isinstance(children, dict):
            for subparent, leaves in children.items():
                keywords.append(subparent)
                if isinstance(leaves, list):
                    keywords.extend(leaves)
                elif isinstance(leaves, dict):
                    keywords.extend(flatten_gcmd_keywords({subparent: leaves}))
        elif isinstance(children, list):
            keywords.extend(children)
    return keywords


def get_leaf_level_keywords(hierarchy):
    """Extract ONLY the deepest/most specific keywords (Level 3)."""
    leaf_keywords = []
    
    def extract_leaves(node):
        if isinstance(node, dict):
            for key, value in node.items():
                extract_leaves(value)
        elif isinstance(node, list):
            leaf_keywords.extend(node)
    
    extract_leaves(hierarchy)
    return sorted(set(leaf_keywords))


GCMD_KEYWORD_LIST = sorted({kw for kw in flatten_gcmd_keywords(GCMD_KEYWORD_HIERARCHY)})
GCMD_KEYWORD_LEAF_LIST = get_leaf_level_keywords(GCMD_KEYWORD_HIERARCHY)
GCMD_KEYWORD_LOOKUP = {normalize_keyword(kw): kw for kw in GCMD_KEYWORD_LIST}


def is_valid_gcmd_keyword(keyword):
    return normalize_keyword(keyword) in GCMD_KEYWORD_LOOKUP


def get_canonical_gcmd_keyword(keyword):
    return GCMD_KEYWORD_LOOKUP.get(normalize_keyword(keyword))


GCMD_KEYWORD_PROMPT_HINT = (
    "Use the Global Change Master Directory (GCMD) keyword taxonomy and STRONGLY FAVOR specific, "
    "deep-level terms over broad category labels. Prioritize the specific leaf-level keywords. "
    "Do not return only parent-level terms like 'Atmosphere', 'Oceans', 'Environment', 'Cryosphere', "
    "or 'Location' unless no specific child-term applies. Instead, use the specific scientific terms like: "
    + ", ".join(GCMD_KEYWORD_LEAF_LIST[:30])
    + ". Always provide specific, detailed keywords that accurately describe the dataset's scientific content."
)
