import threading
from .models import ActivityLog
import requests
import logging
import socket

logger = logging.getLogger(__name__)
_thread_locals = threading.local()

def get_current_request():
    return getattr(_thread_locals, 'request', None)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def get_ip_location(ip_address):
    """Get country and location from IP address using multiple API fallbacks"""
    try:
        if ip_address in ['127.0.0.1', 'localhost']:
            return 'Local', 'Localhost'
        
        # Special case for NCPOR IP
        if ip_address == '172.27.27.27':
            return 'India', 'Goa, India'
        
        # Try ipapi.co first
        try:
            response = requests.get(
                f'https://ipapi.co/{ip_address}/json/', 
                timeout=3,
                headers={'User-Agent': 'NPDC-Site-Hit-Tracker/1.0'}
            )
            if response.status_code == 200:
                data = response.json()
                country = data.get('country_name', 'Unknown')
                city = data.get('city', '')
                location = f"{city}, {country}" if city else country
                logger.info(f"IP geolocation via ipapi.co: {ip_address} -> {country}")
                return country, location
        except requests.exceptions.Timeout:
            logger.debug(f"ipapi.co timeout for {ip_address}, trying fallback...")
        
        # Try ip-api.com as fallback (simpler response)
        try:
            response = requests.get(
                f'http://ip-api.com/json/{ip_address}',
                timeout=2,
                params={'fields': 'country,city,status'}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country = data.get('country', 'Unknown')
                    city = data.get('city', '')
                    location = f"{city}, {country}" if city else country
                    logger.info(f"IP geolocation via ip-api: {ip_address} -> {country}")
                    return country, location
        except Exception as e:
            logger.debug(f"ip-api fallback failed: {e}")
        
        # If all APIs fail, return None
        logger.warning(f"Could not fetch geolocation for IP: {ip_address}")
        return None, None
    except Exception as e:
        logger.error(f"Error in get_ip_location: {e}")
        return None, None

def get_hostname_from_ip(ip_address):
    """Get hostname from IP address using reverse DNS lookup"""
    try:
        if not ip_address or ip_address == '127.0.0.1':
            return socket.gethostname()  # Return local hostname for local IP
        
        # Special case for NCPOR IP
        if ip_address == '172.27.27.27':
            return 'NCPOR'
        
        # Try reverse DNS lookup
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except (socket.herror, socket.gaierror, IndexError) as e:
        # Reverse lookup failed, return None
        logger.debug(f"Could not resolve hostname for IP {ip_address}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error in get_hostname_from_ip: {e}")
        return None
    
    except Exception as e:
        logger.error(f"Error in get_ip_location: {e}")
        return None, None

class ActivityLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # Only log access for these main pages to avoid excessive logging
        self.main_pages = ['/', '/about/', '/contact-us/', '/data-policy/', '/polar-directory/']

    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)
        
        # Log access for anonymous users on main pages
        if (not request.user.is_authenticated and 
            request.method == 'GET' and 
            request.path in self.main_pages):
            ip = get_client_ip(request)
            country, location = get_ip_location(ip)
            hostname = get_hostname_from_ip(ip)
            ActivityLog.objects.create(
                actor=None,  # No actor for anonymous
                action_type='ACCESS',
                ip_address=ip,
                hostname=hostname,
                country=country,
                location=location,
                remarks=f'Anonymous user accessed {request.path}',
                status='SUCCESS',
                path=request.path
            )
        
        return response
