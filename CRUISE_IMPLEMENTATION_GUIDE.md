# Cruise Feature Implementation Guide

## Overview

This document describes the Cruise feature implementation based on the legacy JSP application.

## Features Implemented

### 1. Cruise Summary Page (`/cruise/summary/`)

**Reference**: `cruiseSummary.java`

Features:
- List all research cruises with pagination
- Dynamic filtering by:
  - Ship Name
  - Cruise Number
  - Chief Scientist Name
  - Area
- AJAX-powered dropdown filtering
- Sortable, responsive table layout
- Shows summary statistics (total cruises, filtered count)

### 2. Cruise Detail Page (`/cruise/detail/<id>/`)

Displays detailed information:
- Cruise identification (number, name, ship)
- Schedule (start and end dates)
- Chief scientist and area information
- Scientific objectives and description
- Associated files with download capabilities
- Metadata (creation and update timestamps)

### 3. Secure File Downloads (`/cruise/download/`)

**Reference**: `crusDownload.java`

Security features:
- ✅ **Directory Traversal Prevention**: Blocks `..`, `/`, `\` in filenames
- ✅ **Filename Sanitization**: Only allows `[a-zA-Z0-9_.-]`
- ✅ **Path Validation**: Ensures file path remains within download directory
- ✅ **File Existence Checks**: Returns 404 if file doesn't exist
- ✅ **Content-Type Handling**:
  - PDFs served inline: `application/pdf`
  - Others served as attachments: `application/octet-stream`
- ✅ **Error Handling**: Proper HTTP status codes and error messages

### 4. API Endpoints

#### Get Filter Dropdown
```
GET /cruise/api/dropdown/?type=ship_name
GET /cruise/api/dropdown/?type=cruise_no
GET /cruise/api/dropdown/?type=chief_scientist_name
GET /cruise/api/dropdown/?type=area
```

Returns HTML options for the selected filter type.

#### Cruise List API
```
GET /cruise/api/list/?ship_name=...&cruise_no=...&chief_scientist=...&area=...
```

Returns JSON with filtered cruise data.

## Database Models

### Cruise Model

```python
Fields:
- ship_name: CharField(255)
- cruise_no: CharField(50, unique=True) - Unique identifier
- cruise_name: CharField(255, optional)
- period_from: DateField - Start date
- period_to: DateField - End date
- chief_scientist_name: CharField(255)
- area: CharField(255)
- objective: TextField - Scientific goals
- status: CharField(20) - planned/ongoing/completed/archived
- description: TextField (optional)
- files_link: CharField(500, optional)
- created_at: DateTimeField (auto)
- updated_at: DateTimeField (auto)

Indexes:
- ship_name, cruise_no, chief_scientist_name, area, -period_from
```

### CruiseFile Model

```python
Fields:
- cruise: ForeignKey(Cruise, CASCADE)
- file_name: CharField(500)
- file_type: CharField(20) - report/data/document/image/video/other
- file_path: CharField(500) - Relative path in media/cruise_downloads/
- file_size: BigIntegerField (bytes)
- description: TextField (optional)
- uploaded_at: DateTimeField (auto)
- updated_at: DateTimeField (auto)

Indexes:
- cruise, file_type
```

## File Structure

```
cruise/
├── __init__.py
├── admin.py              # Django admin interface
├── apps.py              # App configuration
├── models.py            # Cruise and CruiseFile models
├── views.py             # View logic with security
├── urls.py              # URL routing
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py  # Initial migration
└── templates/cruise/
    ├── cruise_summary.html   # List page with filters
    └── cruise_detail.html    # Detail page with files
```

## URL Routes

```python
/cruise/summary/                          # Cruise list with filters
/cruise/detail/<id>/                      # Cruise detail
/cruise/download/?filename=...            # Secure file download
/cruise/api/dropdown/?type=...            # Dropdown filter API
/cruise/api/list/?...                     # Cruise data API
```

## Admin Interface

Navigate to `/admin/cruise/` to manage:
- **Cruises**: Add, edit, delete cruise records
- **Cruise Files**: Manage files associated with cruises

## Integration with Existing System

1. **Registered in Django Settings**:
   - Added `cruise.apps.CruiseConfig` to `INSTALLED_APPS`

2. **URL Configuration**:
   - Included in main URL router as `/cruise/`

3. **Media Folder**:
   - Downloads stored in `media/cruise_downloads/`

4. **Static Files**:
   - Uses shared Bootstrap and FontAwesome from base template

## Usage Examples

### Adding a Cruise

1. Go to Django admin: `/admin/`
2. Click **Cruises → Add Cruise**
3. Fill in the fields:
   - Cruise No: `CR-2024-001`
   - Ship Name: `Research Vessel Investigator`
   - Period From/To: Select dates
   - Chief Scientist: `Dr. John Smith`
   - Area: `Southern Ocean`
   - Objective: `Study oceanographic phenomena`
4. Click **Save**

### Uploading Files

1. Go to Django admin: `/admin/cruise/cruisefile/`
2. Click **Add Cruise File**
3. Select the cruise
4. Upload the file
5. Specify file type and description
6. Click **Save**

The file will be stored in `media/cruise_downloads/`

### Searching Cruises

1. Visit `/cruise/summary/`
2. Select a filter type (Ship Name, Cruise Number, etc.)
3. Select or type a value
4. Click **Search**
5. Click a cruise to view details

## Security Considerations

1. **File Upload Restrictions**:
   - Only upload legitimate research files
   - Verify file integrity before uploading
   - Consider file size limits

2. **Validation**:
   - Filename sanitization is strict and intentional
   - Prevents common security vulnerabilities
   - Invalid filenames will be rejected

3. **Access Control**:
   - Currently public (anyone can view/download)
   - Can be restricted to authenticated users if needed
   - Modify views to add `@login_required` decorator

4. **Logging**:
   - File downloads are logged for audit trail
   - Check logs in activity_logs app

## Performance Optimization

1. **Database Indexes**:
   - Indexes on common filter fields improve query speed
   - Large datasets benefit from pagination

2. **Caching** (Future):
   - Dropdown values could be cached
   - Cruise list could implement caching

3. **Pagination**:
   - 10 records per page (adjustable in views.py)
   - Prevents large result sets

## Troubleshooting

### Files not downloading
- Check `media/cruise_downloads/` directory exists
- Verify filename spelling (case-sensitive)
- Check file permissions on the server

### Migrations not applying
```bash
python manage.py migrate cruise
```

### Admin interface issues
- Ensure `cruise.apps.CruiseConfig` is in INSTALLED_APPS
- Clear browser cache
- Check Django logs for errors

## Future Enhancements

1. **Advanced Search**: Full-text search on cruise details
2. **Bulk Upload**: Import cruises from CSV
3. **File Versioning**: Track file changes over time
4. **Access Restrictions**: Limit downloads to authenticated users
5. **Statistics**: Track most downloaded files, popular cruises
6. **Integration**: Link cruises to datasets and publications
7. **Map Visualization**: Show cruise routes on interactive map
8. **Export**: Download cruise data in CSV/Excel format

## Reference to Original JSP Files

The implementation preserves the exact functionality from:
- **cruiseSummary.java**: Core filtering and display logic
- **crusDownload.java**: File download security and validation

All features from the original legacy system have been converted to Django best practices while maintaining security and functionality.
