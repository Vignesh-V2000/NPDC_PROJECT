# NPDC Chatbot Knowledge Base

## Portal Information

### Basic Details
- **Name**: National Polar Data Center (NPDC)
- **Organization**: National Centre for Polar and Ocean Research (NCPOR)
- **Ministry**: Ministry of Earth Sciences, Government of India
- **Location**: Goa, India

### Purpose
NPDC manages and archives scientific datasets from polar and Himalayan research expeditions. It provides standardized metadata management, DOI assignment, and controlled access to research data.

---

## Contact Information

**National Polar Data Center (NPDC)**

- **📍 Address**: Headland Sada, Vasco-da-Gama, Goa, INDIA - 403 804
- **📞 Phone**: 0091-832-2525515
- **✉️ Email**: npdc@ncpor.res.in
- **🕐 Hours**: Mon-Fri: 9:00 AM - 5:00 PM IST

---

## Expedition Types

### 1. Antarctic Expeditions
- Scientific expeditions to Antarctica
- Research areas: Climate, glaciology, marine biology, atmospheric science

### 2. Arctic Expeditions
- Research expeditions to the Arctic region
- Focus: Ice dynamics, ocean currents, polar ecosystems

### 3. Southern Ocean Expeditions
- Marine research in the Southern Ocean
- Studies: Oceanography, marine life, water chemistry

### 4. Himalayan Expeditions
- High-altitude research in the Himalayas
- Focus: Glaciology, climate change, mountain ecosystems

---

## Data Categories

- Atmosphere
- Biosphere
- Cryosphere
- Oceans
- Paleoclimate
- Solid Earth
- Land Surface
- Marine Science
- Terrestrial Science
- Human Dimensions

---

## Dataset Submission Process

### Required Steps
1. Log in to your NPDC account
2. Navigate to Data > Submit New Dataset
3. Fill in identification section (title, abstract, keywords)
4. Select expedition type and project details
5. Enter temporal and spatial coverage
6. Upload data files, metadata, and README
7. Choose access type and license
8. Submit for review

### Required Metadata Fields

#### Identification
- Title (max 220 characters)
- Abstract (max 1000 characters)
- Purpose
- Keywords (GCMD recommended)
- DOI (optional)

#### Project Information
- Expedition Type
- Expedition Year
- Project Name and Number
- Category
- ISO Topic

#### Coverage
- Temporal: Start and End dates
- Spatial: Bounding box (West/East longitude, North/South latitude)

#### Access & Licensing
- Access Type: Open, Restricted, or Embargoed
- License information
- Usage restrictions (if any)

---

## AI-Powered Search Features

The NPDC portal includes an intelligent search system at `/search/` with the following AI features:

### 🐧 Penguin Smart Search
- Toggle on/off with the Smart Search switch on the search page
- When enabled, searches are enhanced with AI capabilities

### Natural Language Query Understanding
- Users can type conversational queries like "show me glacier data from Himalaya 2024"
- The AI parses the query and auto-applies filters (expedition type, year, category, etc.)

### AI Search Summary
- When results are found, an AI-generated summary card appears above results
- Provides a concise overview of what the search results contain

### Zero-Result Recovery
- When 0 results are found, AI suggests alternative search terms
- Detects spelling errors and suggests corrections
- Identifies if a query is outside polar/cryosphere data scope

### Search Tips
- Use quotes for exact phrases like "ice core"
- Start with "10." for DOI search
- Try natural language queries when Smart Search is enabled
- Use sidebar filters (Expedition Type, Category, ISO Topic, Year, Temporal Range, Bounding Box)

---

## AI-Powered Submission Features

The NPDC data submission form includes 9 AI-powered helper tools to streamline the dataset submission process:

### 1. Auto-Classify (Category/Topic)
- Automatically suggests the most appropriate scientific category and ISO topic for your dataset
- Analyzes your title and abstract to recommend the best classification

### 2. Smart Keywords Generator
- Generates relevant scientific keywords and terminology based on your data description
- Helps ensure your dataset is discoverable through GCMD-recommended terminology

### 3. Abstract Quality Checker
- Analyzes your abstract for clarity, completeness, and adherence to standards
- Provides suggestions to improve the quality of your abstract (max 1000 characters)

### 4. Spatial Coordinate Extractor
- Intelligently extracts geographic coordinates from your data or abstract
- Auto-fills the spatial coverage bounding box fields

### 5. Smart Form Pre-fill
- Automatically populates form fields based on your expedition type and dataset information
- Reduces manual data entry and ensures consistency

### 6. Reviewer Assistant
- Provides guidance on common reviewer feedback and requirements
- Helps prepare your submission to pass review on first attempt

### 7. AI Title Generator
- Generates descriptive, searchable titles for your dataset
- Includes expedition name, expedition type, and key data characteristics

### 8. AI Purpose Generator
- Creates a clear statement of purpose describing why your data was collected
- Aligns with NPDC standards and best practices

### 9. Data Resolution Suggester
- Recommends appropriate horizontal, vertical, and temporal resolution values
- Validates resolution values against typical ranges for polar/Himalayan research data

### Data Resolution Fields

When submitting data, you can specify data resolution across three dimensions:

**Horizontal Resolution (Spatial X-Y)**
- Measured in degrees from the equator or prime meridian
- Typical ranges: 0.001° to 5° for polar expeditions
- Format: Degrees and Minutes (or decimal degrees)
- Example: 1.5° = better resolution than 10°

**Vertical Resolution (Spatial Z)**
- Measured in meters or kilometers for depth/altitude
- Typical ranges: 1m to 1000m for oceanographic or atmospheric data
- Can also be specified for ice core or subsurface data
- Example: 10m vertical resolution for water temperature profiles

**Temporal Resolution**
- Frequency of measurements over time
- Common formats: Hourly, Daily, Weekly, Monthly, Yearly
- Can also specify exact intervals (e.g., "Every 6 hours")
- Typical ranges: Sub-hourly to Decadal for polar research

---

## Submission Status Workflow

1. **Draft** - Saved but not submitted
2. **Submitted** - Awaiting reviewer assignment
3. **Under Review** - Being evaluated by reviewer
4. **Approved** - Dataset is published and accessible
5. **Rejected** - Needs revision (can resubmit from draft)

---

*This knowledge base supports the NPDC Portal chatbot. Last updated: February 2026*
