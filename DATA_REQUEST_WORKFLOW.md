# Data Request Workflow

## Overview

When a user submits a "Get Data" request to download a dataset:

1. **Request is logged** — A `DatasetRequest` record is created with user contact info
2. **Email sent immediately** — The requester receives an email with the dataset file attached
3. **Admins notified** — All superusers are CC'd on the email for monitoring
4. **No approval needed** — The old approval/rejection flow has been removed

## Key Components

### Model: DatasetRequest
**File:** [data_submission/models.py](data_submission/models.py)

- `dataset` — ForeignKey to `DatasetSubmission` (the dataset being requested)
- `requester` — Optional ForeignKey to `User` (null for anonymous requests)
- `first_name`, `last_name`, `email` — Requester contact info (required)
- `institute`, `country`, `research_area`, `purpose` — Additional context about the requester
- `agree_cite`, `agree_share` — User agreement checkboxes
- Deprecated fields (`status`, `approved_date`, etc.) — Kept for backwards compatibility but unused

### View: get_data_view()
**File:** [data_submission/views.py#L433](data_submission/views.py)

Handles the dataset download request form:
- **GET:** Displays the request form (pre-fills user info for authenticated users)
- **POST (valid):** 
  - Saves the request to the database
  - Triggers email with dataset attachment
  - Redirects to success page
- **POST (invalid):** Re-displays the form with validation errors

### Email Helper: send_dataset_request_email()
**File:** [data_submission/views.py#L481](data_submission/views.py)

Composes and sends the notification email:
- Extracts metadata: dataset ID, title, temporal range
- Includes download link to the dataset file
- Attaches the actual file from `submission.data_file`
- CC's all superusers (`User.objects.filter(is_superuser=True)`)
- Uses Django's `EmailMultiAlternatives` for formatting

### Form: DatasetRequestForm
**File:** [data_submission/forms.py](data_submission/forms.py)

- Fields:
  - `first_name`, `last_name`, `email` (required)
  - `institute`, `country`, `research_area`, `purpose` (optional)
  - `agree_cite`, `agree_share` (boolean checkboxes)
  - `captcha` (CaptchaField for security)
- Pre-fills user data for authenticated users

## Testing

### Unit Test
Run the test suite:
```bash
python manage.py test data_submission.tests.DataRequestEmailTest.test_request_triggers_email_and_logging -v 2
```

**What it tests:**
- Request is created and linked to dataset
- Request is linked to authenticated user (if logged in)
- Email is sent with correct recipient
- Subject contains "Dataset Request" and metadata ID
- Body includes dataset title and file name
- Superuser emails are in CC list
- Dataset file is properly attached

**Note:** The test uses a modified form without CAPTCHA to simplify testing; CAPTCHA is enforced in production.

### Manual Testing
1. Navigate to a dataset's "Get Data" page
2. Fill in the form (you can be logged in or anonymous)
3. Submit the form
4. You should see:
   - A "success" page or redirect
   - An email in your inbox (if using SMTP) or in Django's email console
   - Admins should also see a CC copy

## Database
### Migration
Migration `0012_add_requester_to_datasetrequest` adds the `requester` field.

Run it with:
```bash
python manage.py migrate
```

### Checking Logged Requests
View all get-data requests in Django admin:
```
/admin/data_submission/datasetrequest/
```

## Configuration

### Email Backend
The email backend is configured in `settings.py`:
- **Development:** `console` backend (prints to console/logs)
- **Production:** Configure with your email provider (SMTP, SendGrid, etc.)

Example for SMTP:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'noreply@npdc.ncpor.res.in'
```

## Timeline of Changes

1. **Removed approval/rejection flow** — `approve_request()` and `reject_request()` views deleted
2. **Removed admin URLs** — No more `/approve/` or `/reject/` endpoints
3. **Added `requester` field** — Links request to authenticated user
4. **Refactored to email-on-request** — Immediately sends email instead of waiting for approval
5. **Simplified templates** — Admin template now shows logs only, no action buttons

## Files Modified
- `data_submission/models.py` — Added `requester` FK, updated `__str__`
- `data_submission/views.py` — Rewrote `get_data_view()`, removed approval functions, added `send_dataset_request_email()`
- `data_submission/urls.py` — Removed `/approve/` and `/reject/` routes
- `data_submission/forms.py` — No changes (form already existed)
- `data_submission/tests.py` — Added `DataRequestEmailTest` test class
- `templates/admin/admin_data_requests.html` — Simplified to show logs only
- Migration `0012_add_requester_to_datasetrequest.py` — Adds `requester` field

## Backwards Compatibility
The old `status` field in `DatasetRequest` still exists but is deprecated and unused. Legacy requests can still be queried by status if needed.
