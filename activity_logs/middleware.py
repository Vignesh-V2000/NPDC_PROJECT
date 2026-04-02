import threading
from .models import ActivityLog

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
            ActivityLog.objects.create(
                actor=None,  # No actor for anonymous
                action_type='ACCESS',
                ip_address=ip,
                remarks=f'Anonymous user accessed {request.path}',
                status='SUCCESS',
                path=request.path
            )
        
        return response
