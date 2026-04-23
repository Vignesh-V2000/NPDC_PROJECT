import os
import logging
from django.shortcuts import render
from django.http import FileResponse, HttpResponse, JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db import connection
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from django.utils.html import escape

logger = logging.getLogger(__name__)


CRUISE_FILTER_COLUMNS = {
    'ship_name': 'ship_name',
    'cruise_no': 'cruise_no',
    'chief_scientist_name': 'chief_scientist_name',
    'area': 'area',
}


def _fetch_all_dicts(query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params or [])
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _fetch_one_dict(query, params=None):
    rows = _fetch_all_dicts(query, params)
    return rows[0] if rows else None


def cruise_summary_view(request):
    """
    Cruise Summary Page - List all cruises with filtering options
    """
    try:
        filter_type = request.GET.get('filter_type', 'all')
        search_value = request.GET.get('search_value', '').strip()
        sql = """
            SELECT ship_name, cruise_no, period_from, period_to,
                   chief_scientist_name, area, objective, files_link
            FROM cruise
        """
        params = []

        if filter_type in CRUISE_FILTER_COLUMNS and search_value:
            sql += f" WHERE {CRUISE_FILTER_COLUMNS[filter_type]} ILIKE %s"
            params.append(f"%{search_value[:200]}%")

        sql += " ORDER BY cruise_no DESC"
        cruises = _fetch_all_dicts(sql, params)

        ship_names = [row['ship_name'] for row in _fetch_all_dicts(
            "SELECT DISTINCT ship_name FROM cruise WHERE ship_name IS NOT NULL AND ship_name <> '' ORDER BY ship_name"
        )]
        chief_scientists = [row['chief_scientist_name'] for row in _fetch_all_dicts(
            "SELECT DISTINCT chief_scientist_name FROM cruise WHERE chief_scientist_name IS NOT NULL AND chief_scientist_name <> '' ORDER BY chief_scientist_name"
        )]
        areas = [row['area'] for row in _fetch_all_dicts(
            "SELECT DISTINCT area FROM cruise WHERE area IS NOT NULL AND area <> '' ORDER BY area"
        )]
        cruise_numbers = [row['cruise_no'] for row in _fetch_all_dicts(
            "SELECT DISTINCT cruise_no FROM cruise WHERE cruise_no IS NOT NULL AND cruise_no <> '' ORDER BY cruise_no"
        )]

        page = request.GET.get('page', 1)
        paginator = Paginator(cruises, 10)
        
        try:
            cruises_page = paginator.page(page)
        except PageNotAnInteger:
            cruises_page = paginator.page(1)
        except EmptyPage:
            cruises_page = paginator.page(paginator.num_pages)

        context = {
            'cruises': cruises_page,
            'ship_names': ship_names,
            'cruise_numbers': cruise_numbers,
            'chief_scientists': chief_scientists,
            'areas': areas,
            'total_cruises': len(_fetch_all_dicts("SELECT cruise_no FROM cruise")),
            'filtered_count': len(cruises),
            'current_filter': filter_type,
            'search_value': search_value,
        }

        return render(request, 'cruise/cruise_summary.html', context)

    except Exception as e:
        logger.error(f"Error in cruise_summary_view: {str(e)}", exc_info=True)
        return render(request, 'cruise/cruise_summary.html', {
            'error': 'An error occurred while loading cruise data.',
            'total_cruises': 0,
            'filtered_count': 0,
        }, status=500)


@require_GET
def get_cruise_dropdown(request):
    """
    AJAX endpoint to get dropdown options for a specific filter type
    """
    try:
        filter_type = request.GET.get('type', '').strip()

        if not filter_type:
            return JsonResponse({'status': 'error', 'message': 'Invalid filter type'}, status=400)

        column = CRUISE_FILTER_COLUMNS.get(filter_type)
        if not column:
            return JsonResponse({'status': 'error', 'message': 'Unknown filter type'}, status=400)

        data = [
            row[column] for row in _fetch_all_dicts(
                f"SELECT DISTINCT {column} FROM cruise WHERE {column} IS NOT NULL AND {column} <> '' ORDER BY {column}"
            )
        ]

        html = '<option value="">-- Select --</option>'
        for item in data:
            if item:
                html += f'<option value="{escape(item)}">{escape(item)}</option>'

        return HttpResponse(html)

    except Exception as e:
        logger.error(f"Error in get_cruise_dropdown: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Server error'}, status=500)


@require_GET
def cruise_detail(request, cruise_no):
    """
    Display detailed information about a specific cruise
    """
    try:
        cruise = _fetch_one_dict(
            """
            SELECT ship_name, cruise_no, period_from, period_to,
                   chief_scientist_name, area, objective, files_link
            FROM cruise
            WHERE cruise_no = %s
            """,
            [cruise_no],
        )
        if not cruise:
            return render(request, 'cruise/error.html', {'error': 'Cruise not found'}, status=404)

        context = {
            'cruise': cruise,
        }

        return render(request, 'cruise/cruise_detail.html', context)

    except Exception as e:
        logger.error(f"Error in cruise_detail: {str(e)}", exc_info=True)
        return render(request, 'cruise/error.html', {'error': 'Cruise not found'}, status=404)


@require_GET
def download_cruise_file(request):
    """
    Secure file download handler with validation
    References the old crusDownload.java implementation
    """
    try:
        filename = request.GET.get('filename', '').strip()

        # ====== SECURITY CHECKS ======
        
        # 1. Validate filename is not empty
        if not filename:
            logger.warning("Download attempt with empty filename")
            return HttpResponse('Filename is missing', status=400)

        # 2. Prevent directory traversal attacks
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.warning(f"Download attempt with invalid filename: {filename}")
            return HttpResponse('Invalid filename', status=400)

        # 3. Sanitize filename - only allow alphanumeric, dots, hyphens, underscores
        import re
        if not re.match(r'^[\w\-\.]+$', filename):
            logger.warning(f"Download attempt with unsanitized filename: {filename}")
            return HttpResponse('Invalid filename', status=400)

        # 4. Define the download directory
        download_dir = os.path.join(settings.BASE_DIR, 'media', 'cruise_downloads')
        
        # 5. Build the full file path
        file_path = os.path.join(download_dir, filename)

        # 6. Verify the file path is within the allowed directory (prevent escape)
        if not os.path.abspath(file_path).startswith(os.path.abspath(download_dir)):
            logger.warning(f"Download attempt with escaped path: {file_path}")
            return HttpResponse('Invalid file path', status=400)

        # 7. Check if file exists and is a file (not directory)
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            logger.warning(f"Download attempt for non-existent file: {file_path}")
            return HttpResponse('File not found', status=404)

        # 8. Set appropriate content type based on file extension
        if filename.endswith('.pdf'):
            content_type = 'application/pdf'
            disposition = f'inline; filename="{filename}"'
        else:
            content_type = 'application/octet-stream'
            disposition = f'attachment; filename="{filename}"'

        # 9. Open and serve the file
        try:
            file_handle = open(file_path, 'rb')
            response = FileResponse(file_handle, content_type=content_type)
            response['Content-Disposition'] = disposition
            
            logger.info(f"File downloaded successfully: {filename}")
            return response

        except IOError as io_error:
            logger.error(f"IO Error reading file {file_path}: {str(io_error)}", exc_info=True)
            return HttpResponse('Error reading file', status=500)

    except Exception as e:
        logger.error(f"Error in download_cruise_file: {str(e)}", exc_info=True)
        return HttpResponse('Server error', status=500)


@require_GET
def cruise_api_list(request):
    """
    API endpoint to get cruise data as JSON
    Supports filtering
    """
    try:
        sql = """
            SELECT ship_name, cruise_no, period_from, period_to,
                   chief_scientist_name, area, objective, files_link
            FROM cruise
            WHERE 1=1
        """
        params = []

        ship_name = request.GET.get('ship_name', '').strip()
        cruise_no = request.GET.get('cruise_no', '').strip()
        chief_scientist = request.GET.get('chief_scientist', '').strip()
        area = request.GET.get('area', '').strip()

        if ship_name:
            sql += " AND ship_name ILIKE %s"
            params.append(f"%{ship_name[:100]}%")
        if cruise_no:
            sql += " AND cruise_no ILIKE %s"
            params.append(f"%{cruise_no[:50]}%")
        if chief_scientist:
            sql += " AND chief_scientist_name ILIKE %s"
            params.append(f"%{chief_scientist[:100]}%")
        if area:
            sql += " AND area ILIKE %s"
            params.append(f"%{area[:100]}%")

        sql += " ORDER BY cruise_no DESC"
        cruises = _fetch_all_dicts(sql, params)

        cruise_list = [
            {
                'cruise_no': cruise['cruise_no'],
                'ship_name': cruise['ship_name'],
                'chief_scientist_name': cruise['chief_scientist_name'],
                'area': cruise['area'],
                'period_from': cruise['period_from'].isoformat() if cruise['period_from'] else None,
                'period_to': cruise['period_to'].isoformat() if cruise['period_to'] else None,
                'files_link': cruise['files_link'],
            }
            for cruise in cruises
        ]

        return JsonResponse({
            'status': 'success',
            'count': len(cruise_list),
            'data': cruise_list
        })

    except Exception as e:
        logger.error(f"Error in cruise_api_list: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
