"""
Fix all Django templates to use {% load static %} and {% static %} tags.
"""
import os
import re

TEMPLATES_DIR = 'templates'

# Mapping of old asset references to new {% static %} references
STATIC_REPLACEMENTS = [
    # CSS link
    ('href="style.css"',   "href=\"{% static 'css/style.css' %}\""),
    # JS script
    ('src="script.js"',    "src=\"{% static 'js/script.js' %}\""),
    # Images in assets folder
    ('src="assets/biko_bilao_1778184493482.png"',    "src=\"{% static 'images/biko_bilao_1778184493482.png' %}\""),
    ('src="assets/biko_container_1778184629253.png"', "src=\"{% static 'images/biko_container_1778184629253.png' %}\""),
    ('src="assets/biko_story_1778184640063.png"',    "src=\"{% static 'images/biko_story_1778184640063.png' %}\""),
    ('src="assets/map_placeholder_1778184692126.png"',"src=\"{% static 'images/map_placeholder_1778184692126.png' %}\""),
]

html_files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith('.html')]
changed = []

for filename in html_files:
    filepath = os.path.join(TEMPLATES_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 1. Add {% load static %} at the very top if not already present
    if '{% load static %}' not in content:
        content = '{% load static %}\n' + content

    # 2. Replace static asset references
    for old, new in STATIC_REPLACEMENTS:
        content = content.replace(old, new)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        changed.append(filename)
        print(f"  Updated: {filename}")
    else:
        print(f"  Skipped (no changes): {filename}")

print(f"\nDone. {len(changed)} file(s) updated.")
