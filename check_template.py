import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')
django.setup()

from django.template.loader import get_template
from django.template.exceptions import TemplateSyntaxError

try:
    template = get_template('search/search.html')
    print("Template loaded successfully!")
except TemplateSyntaxError as e:
    print(f"TemplateSyntaxError: {e}")
    print(f"Line number: {e.lineno}")
    print(f"Error: {e.msg}")
