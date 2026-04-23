# Cruise Feature - Quick Start Guide

## ✅ Implementation Complete!

All cruise functionality from the legacy JSP website has been implemented in Django.

## What's New

### 📋 Features
1. **Cruise Summary Page** - Browse all research cruises with advanced filtering
2. **Cruise Detail Page** - View complete cruise information and associated files
3. **Secure File Downloads** - Download cruise documents with validated security
4. **Admin Interface** - Manage cruises and files in Django admin
5. **API Endpoints** - JSON APIs for programmatic access

### 🔒 Security Features Implemented
- ✅ Directory traversal attack prevention
- ✅ Filename validation and sanitization
- ✅ File existence verification
- ✅ Content-type handling (PDF inline, others as attachments)
- ✅ Comprehensive error handling with proper HTTP status codes

---

## 🚀 Getting Started

### Access the Feature

1. **View Cruises**
   - URL: `http://localhost:8000/cruise/summary/`
   - Browse all research cruises with pagination
   - Filter by Ship Name, Cruise Number, Chief Scientist, or Area

2. **Manage Cruises (Admin)**
   - URL: `http://localhost:8000/admin/cruise/`
   - Login with superuser account
   - Add, edit, delete cruises
   - Upload and manage cruise files

3. **Download Files**
   - URL: `http://localhost:8000/cruise/download/?filename=FILE_NAME`
   - Secure download endpoint with validation

---

## 📁 File Structure

```
cruise/
├── models.py              ← Cruise and CruiseFile models
├── views.py               ← All view logic with security
├── urls.py                ← URL routing
├── admin.py               ← Django admin configuration
├── apps.py                ← App configuration
├── migrations/
│   └── 0001_initial.py    ← Database schema
└── templates/cruise/
    ├── cruise_summary.html ← List page with filters
    └── cruise_detail.html  ← Detail page with files

media/cruise_downloads/   ← Downloaded files stored here
```

---

## 📊 Database Models

### Cruise Model
| Field | Type | Notes |
|-------|------|-------|
| cruise_no | CharField(50) | ✅ Unique identifier |
| ship_name | CharField(255) | Indexed for fast searching |
| chief_scientist_name | CharField(255) | Indexed for filtering |
| area | CharField(255) | Indexed for filtering |
| period_from | DateField | Cruise start date |
| period_to | DateField | Cruise end date |
| objective | TextField | Scientific goals |
| status | CharField(20) | planned/ongoing/completed/archived |

### CruiseFile Model
| Field | Type | Notes |
|-------|------|-------|
| cruise | ForeignKey | Links to Cruise |
| file_name | CharField(500) | Original filename |
| file_type | CharField(20) | report/data/document/image/video |
| file_path | CharField(500) | Path in media/cruise_downloads/ |
| file_size | BigIntegerField | Size in bytes |

---

## 🔗 URL Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/cruise/summary/` | GET | Cruise listing with filters |
| `/cruise/summary/?filter_type=...&search_value=...` | GET | Filtered results |
| `/cruise/detail/<id>/` | GET | View cruise details and files |
| `/cruise/download/?filename=...` | GET | Secure file download |
| `/cruise/api/dropdown/?type=...` | GET | Get filter options (AJAX) |
| `/cruise/api/list/?ship_name=...` | GET | Get cruise data as JSON |

---

## 💾 Adding Data

### Method 1: Django Admin (Easiest)

```
1. Go to http://localhost:8000/admin/
2. Click "Cruises" → "Add Cruise"
3. Fill in the fields:
   - Cruise No: CR-2024-001
   - Ship Name: Research Vessel Investigator
   - Chief Scientist: Dr. Smith
   - Area: Southern Ocean
   - Objective: Study oceanographic phenomena
4. Click "Save"
```

### Method 2: Python Shell

```bash
python manage.py shell

>>> from cruise.models import Cruise
>>> from datetime import date
>>> 
>>> Cruise.objects.create(
...     cruise_no='CR-2024-002',
...     ship_name='Polar Explorer',
...     chief_scientist_name='Dr. Jane Doe',
...     area='Antarctic',
...     period_from=date(2024, 1, 1),
...     period_to=date(2024, 3, 31),
...     objective='Polar research expedition',
...     status='completed'
... )
```

### Method 3: Upload Files

```
1. Go to http://localhost:8000/admin/cruise/cruisefile/
2. Click "Add Cruise File"
3. Select the cruise
4. Upload the file
5. Fill in file type and description
6. Click "Save"
```

---

## 🧪 Testing the Feature

### Test Search Filtering
```
1. Go to /cruise/summary/
2. Select "Ship Name" from dropdown
3. Wait for options to load (AJAX)
4. Select a value or type
5. Click "Search"
```

### Test File Download
```
1. Go to /cruise/summary/
2. Click "View" on a cruise with files
3. Click "Download" button
4. File downloads securely
```

### Test Invalid Access
```
Try: /cruise/download/?filename=../../etc/passwd
Result: ❌ Blocked (400 Bad Request)

Try: /cruise/download/?filename=nonexistent.pdf
Result: ❌ Not Found (404)
```

---

## 🛠️ Configuration

### Media Upload Path
Configured in Django settings:
```python
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

### Download Directory
```python
download_dir = os.path.join(settings.BASE_DIR, 'media', 'cruise_downloads')
```

---

## 📝 API Examples

### Get All Cruises as JSON
```bash
curl http://localhost:8000/cruise/api/list/
```

### Filter Cruises
```bash
curl "http://localhost:8000/cruise/api/list/?ship_name=Investigator&area=Antarctic"
```

### Get Dropdown Options
```bash
curl "http://localhost:8000/cruise/api/dropdown/?type=ship_name"
```

### Download File
```bash
curl -O "http://localhost:8000/cruise/download/?filename=report.pdf"
```

---

## ⚠️ Important Security Notes

1. **Filename Restrictions**
   - Only `[a-zA-Z0-9_.-]` allowed
   - Length limited to 500 characters
   - No directory traversal (`..`, `/`, `\`)

2. **File Location**
   - All files must be in `media/cruise_downloads/`
   - Files outside this directory cannot be accessed

3. **Content Types**
   - PDFs served inline (safe viewing)
   - Other files as attachments (safe download)

4. **Access Control**
   - Currently public (no login required)
   - Can add `@login_required` to restrict

---

## 🐛 Troubleshooting

### "Download directory doesn't exist"
```bash
mkdir media/cruise_downloads
```

### "Migration not applied"
```bash
python manage.py migrate cruise
```

### "Admin page shows migration conflicts"
```bash
python manage.py migrate cruise --fake-initial
python manage.py migrate cruise
```

### "Files not appearing in table"
- Check file exists in `media/cruise_downloads/`
- Verify filename in CruiseFile record
- Check file permissions

---

## 📚 Additional Resources

- **Full Documentation**: See [CRUISE_IMPLEMENTATION_GUIDE.md](CRUISE_IMPLEMENTATION_GUIDE.md)
- **Legacy Reference**: Original JSP files (cruiseSummary.java, crusDownload.java)
- **Django Docs**: https://docs.djangoproject.com/

---

## ✨ What Was Migrated From JSP

| JSP Feature | Django Equivalent | Status |
|-------------|------------------|--------|
| Cruise listing with pagination | `cruise_summary.html` | ✅ Complete |
| Filter dropdowns (AJAX) | `get_cruise_dropdown()` view | ✅ Complete |
| Dynamic search | `cruise_summary_view()` filtering | ✅ Complete |
| File download handler | `download_cruise_file()` view | ✅ Complete |
| Directory traversal protection | Filename sanitization | ✅ Improved |
| File existence validation | File path checking | ✅ Enhanced |
| Content-type handling | PDF vs. binary detection | ✅ Complete |

---

## 🎯 Next Steps

1. **Add Sample Data**: Use Django admin to add sample cruises
2. **Test Features**: Browse, search, and download files
3. **Customize Styling**: Modify template CSS to match your design
4. **Add Permissions**: Restrict to authenticated users if needed
5. **Implement Caching**: Cache dropdown values for performance

---

## 📞 Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review [CRUISE_IMPLEMENTATION_GUIDE.md](CRUISE_IMPLEMENTATION_GUIDE.md)
3. Check Django logs for detailed error messages
4. Review Python stack traces in console

---

**Implementation Date**: April 23, 2026  
**Status**: ✅ Ready for Production  
**Security**: ✅ Hardened against common attacks
