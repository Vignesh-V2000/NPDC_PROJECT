# NPDC Chatbot Knowledge Base

## Portal Information

### Basic Details
- **Name**: National Polar Data Center (NPDC)
- **Organization**: National Centre for Polar and Ocean Research (NCPOR)
- **Ministry**: Ministry of Earth Sciences, Government of India
- **Location**: Goa, India
- **Email**: npdc@ncpor.res.in
- **Website**: https://www.npdc.ncpor.res.in/

### Purpose
NPDC manages and archives scientific datasets from polar and Himalayan research expeditions. It provides standardized metadata management, DOI assignment, and controlled access to research data.

---

## Contact Information

**National Polar Data Center (NPDC)**

- **📍 Address**: Headland Sada, Vasco-da-Gama, Goa, INDIA - 403 804
- **📞 Phone**: 0091-832-2525515
- **✉️ Email**: npdc@ncpor.res.in

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
1. Log in to your NPDC account (account must be approved by NPDC)
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

- Register at `/register/` — requires name, email, organisation, organisation URL, and designation
- Additional optional fields: title (Mr/Ms/Dr/Prof), preferred name, profile URL, phone, WhatsApp number, alternate email, address
- New accounts are **pending by default** and must be approved by NPDC before login is allowed
- NPDC manages approvals at `/staff/user-approval/`
- Forgot password: `/forgot-password/` → reset via emailed link at `/reset-password/`

---

## User Dashboard

After login, users see their personal dashboard at `/dashboard/`:

### For Regular Users (Participants)
- View total submitted datasets and published count
- Recent submission activity (latest 5 non-draft submissions)
- Quick links to submit new data or view existing submissions

### My Submissions (`/data/my-submissions/`)
- View all your own dataset submissions
- Track status of each submission (Draft, Submitted, Under Review, Published, etc.)

---

## Admin Roles & Access Control (RBAC)

NPDC uses a role-based access control system with three admin types:

### 1. Super Admin
- Django superuser (`is_superuser=True`)
- **Full access** to every feature: dashboard, all datasets, review queue, data requests, user approvals, create users/admins, system logs, system reports, dataset deletion, and Django admin panel (`/admin/`)

### 2. Normal Admin
- Staff user (`is_staff=True`) with no expedition type assigned
- Same access as Super Admin **except** no access to the Django admin panel (`/admin/`)
- Can delete datasets, manage users, view system logs

### 3. Expedition Admin (Child Admin)
- Staff user with a specific expedition type assigned (Antarctic, Arctic, Southern Ocean, or Himalaya)
- Can **only** see and review datasets matching their assigned expedition type
- **Cannot** access: user approvals, create users, system logs, system reports, or delete datasets
- Sees a filtered view of the dashboard, review queue, all datasets, and data requests — limited to their expedition type

---

## Admin Panel & Navigation

Staff users access the admin panel via `/data/admin/dashboard/`. The admin sidebar includes:

### All Admin Types
1. **Dashboard** (`/data/admin/dashboard/`) — Overview with stats: pending reviews, total submissions, active users, published datasets, and recent activity feed
2. **All Datasets** (`/data/admin/all/`) — Browse every dataset (Published, Draft, Submitted, etc.) with search, status filter, expedition filter, category filter, and date range filter. Paginated (10 per page)
3. **Review Queue** (`/data/admin/review/`) — Shows datasets with status "Submitted" or "Under Review", with search and filters. Expedition Admins only see their expedition type
4. **Data Requests** (`/data/admin/data-requests/`) — View all data download requests from researchers including requester details, dataset info, expedition type, request location/IP, and purpose

### Super Admin & Normal Admin Only
5. **User Approvals** (`/staff/user-approval/`) — Manage pending registrations; approve, reject, or view/edit user details
6. **Create Admin** (`/staff/create-user/`) — Create new standard users (pre-approved) or new admin users with optional expedition type
7. **System Log** (`/logs/system-logs/`) — View all system activity logs with filtering by action type, user, and date range. Supports CSV export
8. **System Report** (`/logs/system-report/`) — Download a system metrics CSV with user and dataset statistics

---

## Admin: Dataset Review Workflow

### Reviewing a Submission
1. Navigate to **Review Queue** → click on a submission
2. Review detail page (`/data/admin/review/<metadata_id>/`) shows full metadata, spatial coverage, temporal coverage, files, and scientist details
3. Admin can add **reviewer notes** and change the status

### Status Transitions (Admin Actions)
- `Submitted` → `Published` (approve and publish the dataset)
- Published datasets cannot be changed back

### Automatic Notifications
- When a dataset is published, the submitter receives an email with dataset ID, title, publication date, and a link to view their submissions

### Audit Trail
- Every review action records who reviewed it (`reviewed_by`) and when (`reviewed_at`, `status_updated_at`)

---

## Admin: User Management

### User Approval Dashboard (`/staff/user-approval/`)
Shows four tabs:
- **Pending Users** — New registrations awaiting approval (`is_active=False`, not rejected)
- **Approved Users** — Active standard users (non-staff)
- **Admin Users** — Active staff users
- **Rejected Users** — Users marked as rejected

### Actions on Users
- **View Details** (`/staff/user/<id>/`) — See full registration information
- **Edit Details** (`/staff/user/<id>/edit/`) — Modify user data; includes three actions:
  - **Approve** — Activates the user account, sets `is_approved=True`
  - **Reject** — Marks the user as rejected (does not delete the record)
  - **Request Info** — Sends a custom email to the user asking for additional information
- **Change Password** (`/staff/user/<id>/change-password/`) — Admin can reset any user's password

### Creating Users
At `/staff/create-user/`, admins can create:
- **Standard User** — A regular researcher account, auto-approved on creation
- **Admin User** — A staff account with optional expedition type assignment (Antarctic, Arctic, Southern Ocean, or Himalaya)

---

## Admin: Dataset Management

- **Edit Dataset** (`/data/admin/edit/<metadata_id>/`) — Admin can edit any dataset's metadata
- **Delete Dataset** (`/data/admin/delete/<metadata_id>/`) — Permanently delete a dataset. **Only Super Admins and Normal Admins** can delete; Expedition Admins cannot

---

## Data Access Requests

- Published datasets can be requested by logged-in users via `/data/get-data/<id>/`
- The requester fills out a form with their name, email, institute, country, research area, and purpose
- Upon submission, the dataset is **emailed directly** to the requester (no approval/rejection workflow)
- All requests are **logged** and visible to admins at `/data/admin/data-requests/` for monitoring purposes
- Request details tracked: requester info, dataset, request date, IP address, and geo-location

---

## Dataset Export

- Any published dataset can be exported as an XML metadata file at `/data/export/xml/<metadata_id>/`

---

## Polar Directory & Stations

- `/polar-directory/` — lists polar research stations and associated researchers/data
- `/station/<station_name>/` — detailed page for an individual station

---

## Activity Logs & System Monitoring

### System Logs (`/logs/system-logs/`)
- Tracks all system activity: user logins, dataset submissions, review actions, etc.
- Filterable by action type, user, and date range
- Supports CSV export for offline analysis
- Available to Super Admins and Normal Admins only

### System Report (`/logs/system-report/`)
- Generates a CSV report with key system metrics:
  - Total/active/staff/superuser counts
  - New users in last 30 days
  - Dataset submission counts by status
  - Activity log counts (total and last 30 days)

---

*This knowledge base supports the NPDC Portal chatbot. Last updated: March 2026*
