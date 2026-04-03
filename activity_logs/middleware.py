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
        
        # Check if it's a private/internal IP that can't be geolocated
        if ip_address.startswith(('10.', '172.', '192.168.', '127.')):
            return 'Private Network', 'Internal Network'
        
        # Try multiple geolocation APIs with fallbacks
        
        # 1. Try ipapi.co first
        try:
            response = requests.get(
                f'https://ipapi.co/{ip_address}/json/', 
                timeout=5,
                headers={'User-Agent': 'NPDC-Site-Hit-Tracker/1.0'}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('error') is None:  # No error in response
                    country = data.get('country_name', 'Unknown')
                    city = data.get('city', '')
                    region = data.get('region', '')
                    if city and region:
                        location = f"{city}, {region}, {country}"
                    elif city:
                        location = f"{city}, {country}"
                    else:
                        location = country
                    logger.info(f"IP geolocation via ipapi.co: {ip_address} -> {location}")
                    return country, location
        except Exception as e:
            logger.debug(f"ipapi.co failed for {ip_address}: {e}")
        
        # 2. Try ip-api.com as second option
        try:
            response = requests.get(
                f'http://ip-api.com/json/{ip_address}',
                timeout=5,
                params={'fields': 'country,city,region,status,message'}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    country = data.get('country', 'Unknown')
                    city = data.get('city', '')
                    region = data.get('region', '')
                    if city and region:
                        location = f"{city}, {region}, {country}"
                    elif city:
                        location = f"{city}, {country}"
                    else:
                        location = country
                    logger.info(f"IP geolocation via ip-api: {ip_address} -> {location}")
                    return country, location
        except Exception as e:
            logger.debug(f"ip-api failed for {ip_address}: {e}")
        
        # 3. Try ipinfo.io as third option
        try:
            response = requests.get(
                f'https://ipinfo.io/{ip_address}/json',
                timeout=5,
                headers={'User-Agent': 'NPDC-Site-Hit-Tracker/1.0'}
            )
            if response.status_code == 200:
                data = response.json()
                if 'country' in data:  # Success response
                    country = data.get('country', 'Unknown')
                    city = data.get('city', '')
                    region = data.get('region', '')
                    if city and region:
                        location = f"{city}, {region}, {country}"
                    elif city:
                        location = f"{city}, {country}"
                    else:
                        location = country
                    logger.info(f"IP geolocation via ipinfo.io: {ip_address} -> {location}")
                    return country, location
        except Exception as e:
            logger.debug(f"ipinfo.io failed for {ip_address}: {e}")
        
        # 4. Try ipwhois.app as fourth option
        try:
            response = requests.get(
                f'https://ipwhois.app/json/{ip_address}',
                timeout=5,
                headers={'User-Agent': 'NPDC-Site-Hit-Tracker/1.0'}
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and 'country' in data:
                    country = data.get('country', 'Unknown')
                    city = data.get('city', '')
                    region = data.get('region', '')
                    if city and region:
                        location = f"{city}, {region}, {country}"
                    elif city:
                        location = f"{city}, {country}"
                    else:
                        location = country
                    logger.info(f"IP geolocation via ipwhois.app: {ip_address} -> {location}")
                    return country, location
        except Exception as e:
            logger.debug(f"ipwhois.app failed for {ip_address}: {e}")
        
        # If all APIs fail, return Unknown
        logger.warning(f"Could not fetch geolocation for IP: {ip_address} from any API")
        return 'Unknown', 'Unknown Location'
    except Exception as e:
        logger.error(f"Error in get_ip_location: {e}")
        return 'Unknown', 'Unknown Location'

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
