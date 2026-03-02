from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from urllib.parse import quote
from django.urls import reverse

u = User.objects.get(pk=238)
token = default_token_generator.make_token(u)
uidb64 = urlsafe_base64_encode(force_bytes(u.pk))
token_quoted = quote(token, safe='')
print('token =', token)
print('quoted =', token_quoted)
print('path =', reverse('users:reset_password_confirm', kwargs={'uidb64': uidb64, 'token': token_quoted}))
