from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

def test_view(request):
    raise Exception("TEST EXCEPTION")
    return HttpResponse("TEST VIEW CALLED")

urlpatterns = [
    path('admin/', admin.site.urls),
    path('test/', test_view),

    # ✅ Users app handles login/logout/register
    path('', include('users.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    # ✅ Dataset submission
    path('data/', include('data_submission.urls')),
    path('logs/', include('activity_logs.urls')),
    path('captcha/', include('captcha.urls')),
    # ✅ AI Chatbot Assistant
    path('chatbot/', include('chatbot.urls')),
    path("search/", include("npdc_search.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
