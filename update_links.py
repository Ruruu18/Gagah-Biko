import os, glob

replacements = {
    'href="index.html"': 'href="/"',
    'href="menu.html"': 'href="/menu/"',
    'href="about.html"': 'href="/about/"',
    'href="contact.html"': 'href="/contact/"',
    'href="signup.html"': 'href="/signup/"',
    'href="login.html"': 'href="/login/"',
    'href="checkout.html"': 'href="/checkout/"',
    'href="order_success.html"': 'href="/order-success/"'
}

html_files = glob.glob('templates/*.html')
for file in html_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for old, new in replacements.items():
        content = content.replace(old, new)
        
    # Also add {% csrf_token %} if signup or checkout
    if 'signup.html' in file or 'checkout.html' in file:
        if '{% csrf_token %}' not in content:
            content = content.replace('<body>', '<body>\n  <form style="display:none">{% csrf_token %}</form>')

    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
