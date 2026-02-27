#!/usr/bin/env python
"""Test if the search template loads without errors"""
import os
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'npdc_site.settings')

import django
django.setup()

from django.template.loader import get_template
from django.template.exceptions import TemplateSyntaxError

try:
    print("Testing search template...")
    template = get_template('search/search.html')
    print("✓ Template loaded successfully!")
    print("✓ No syntax errors found")
except TemplateSyntaxError as e:
    print(f"✗ TemplateSyntaxError: {e.msg}")
    print(f"✗ Line number: {e.lineno}")
    print(f"✗ Source: {e.source_name}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
