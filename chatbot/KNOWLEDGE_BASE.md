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

- Agriculture
- Atmosphere
- Biological Classification
- Biosphere
- Climate Indicators
- Cryosphere
- Human Dimensions
- Land Surface
- Marine Science
- Oceans
- Paleoclimate
- Solid Earth
- Spectral/Engineering
- Sun-Earth Interactions
- Terrestrial Hydrosphere
- Terrestrial Science
- Wind Profiler Radar
- Geotectonic Studies
- Audio Signals

---

## Dataset Submission Process

### Required Steps
1. Log in to your NPDC account (account must be approved by NPDC staff)
2. Read submission instructions at `/data/submit/instructions/`
3. Fill in the metadata form: title, abstract, keywords, expedition details, temporal and spatial coverage
4. Upload data files, metadata file, and README on the file upload step
5. Submit for review

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

---

## Search Features

### Main Search (`/search/`)
- Full-text and filter-based search with sidebar filters (Expedition Type, Category, ISO Topic, Year, Temporal Range, Bounding Box)
- Use quotes for exact phrases like "ice core"; start with "10." for DOI search
- Browse by keyword: `/search/browse/keyword/`
- Browse by location: `/search/browse/location/`

### 🐧 Penguin Assist (AI Search)
- Toggle on/off with the Smart Search switch on the main search page
- Understands natural language queries like "show me glacier data from Himalaya 2024" and auto-applies filters
- Generates a summary card above results when datasets are found
- Suggests alternative terms and corrections when no results are found

### AI Search Page (`/search/ai-search/`)
- Dedicated RAG-based (Retrieval-Augmented Generation) AI search interface
- Ask questions in plain language to find relevant datasets

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

1. **Draft** - Saved but not submitted; submitter can edit freely
2. **Submitted** - Sent for review; awaiting staff action
3. **Under Review** - Being evaluated by a reviewer
4. **Needs Revision** - Reviewer has requested changes; submitter must update and resubmit
5. **Published** - Approved and publicly accessible

Note: "Approved" and "Rejected" are not statuses in this system. The terminal positive state is **Published**; the revision state is **Needs Revision**.

---

## User Accounts & Registration

- Register at `/register/` — requires name, organisation, organisation URL, and designation
- New accounts are **pending by default** and must be approved by NPDC staff before login is allowed
- Staff manage approvals at `/staff/user-approval/`
- Forgot password: `/forgot-password/` → reset via emailed link at `/reset-password/`

---

## Data Access Requests

- Restricted or embargoed datasets can be requested by logged-in users via `/data/get-data/<id>/`
- NPDC staff review and approve/reject requests at `/data/admin/data-requests/`
- Requester is notified by email on approval or rejection

---

## Dataset Export

- Any published dataset can be exported as an XML metadata file at `/data/export/xml/<metadata_id>/`

---

## Polar Directory & Stations

- `/polar-directory/` — lists polar research stations and associated researchers/data
- `/station/<station_name>/` — detailed page for an individual station

---

*This knowledge base supports the NPDC Portal chatbot. Last updated: March 2026*
