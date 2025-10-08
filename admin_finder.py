import requests
import argparse
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template_string, request, flash

# --- Configuration ---
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
TIMEOUT = 10
WORDLIST_PATH = 'admin_wordlist_cleaned.txt'

# --- HTML Templates ---

# Template for the main page with the input form
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Panel Finder</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
        }
        .loader {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body class="bg-gray-900 text-white flex items-center justify-center min-h-screen">
    <div class="w-full max-w-2xl bg-gray-800 p-8 rounded-lg shadow-2xl">
        <h1 class="text-3xl font-bold text-center text-cyan-400 mb-2">Admin Panel Finder Pro</h1>
        <p class="text-center text-gray-400 mb-6">Enter a target URL to scan for admin login pages.</p>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
          {% if messages %}
            {% for category, message in messages %}
              <div class="p-4 mb-4 text-sm rounded-lg {{ 'bg-red-800 text-red-300' if category == 'error' else 'bg-blue-800 text-blue-300' }}" role="alert">
                {{ message }}
              </div>
            {% endfor %}
          {% endif %}
        {% endwith %}

        <form method="POST" action="/scan" id="scan-form">
            <div class="flex flex-col sm:flex-row gap-4">
                <input type="url" name="url" class="flex-grow bg-gray-700 text-white border border-gray-600 rounded-md p-3 focus:ring-2 focus:ring-cyan-500 focus:outline-none" placeholder="https://example.com" required>
                <button type="submit" id="submit-button" class="bg-cyan-600 hover:bg-cyan-700 text-white font-bold py-3 px-6 rounded-md transition duration-300 flex items-center justify-center">
                    <span id="button-text">Start Scan</span>
                    <div id="loader" class="loader hidden ml-3" style="width: 20px; height: 20px; border-width: 2px;"></div>
                </button>
            </div>
        </form>
    </div>

    <script>
        document.getElementById('scan-form').addEventListener('submit', function() {
            document.getElementById('button-text').classList.add('hidden');
            document.getElementById('loader').classList.remove('hidden');
            document.getElementById('submit-button').disabled = true;
        });
    </script>
</body>
</html>
"""

# Template to display the scan results
RESULTS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scan Results</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
    </style>
</head>
<body class="bg-gray-900 text-white flex items-center justify-center min-h-screen p-4">
    <div class="w-full max-w-4xl bg-gray-800 p-8 rounded-lg shadow-2xl">
        <h1 class="text-3xl font-bold text-center text-cyan-400 mb-4">Scan Results for <span class="text-white">{{ target_url }}</span></h1>
        
        {% if found_panels %}
            <p class="text-lg text-center text-green-400 mb-6">Found {{ found_panels|length }} potential admin panel(s)!</p>
            <div class="bg-gray-900 rounded-lg p-4 overflow-x-auto">
                <table class="min-w-full">
                    <thead>
                        <tr>
                            <th class="text-left text-gray-400 p-3">URL</th>
                            <th class="text-left text-gray-400 p-3">Status Code</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for panel in found_panels %}
                        <tr class="border-t border-gray-700 hover:bg-gray-700/50">
                            <td class="p-3"><a href="{{ panel.url }}" target="_blank" class="text-cyan-400 hover:underline">{{ panel.url }}</a></td>
                            <td class="p-3 text-green-400">{{ panel.status }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        {% else %}
            <p class="text-lg text-center text-red-400 my-8">No admin panels found for this target.</p>
        {% endif %}
        
        <div class="text-center mt-8">
            <a href="/" class="bg-cyan-600 hover:bg-cyan-700 text-white font-bold py-3 px-6 rounded-md transition duration-300">Scan Another Site</a>
        </div>
    </div>
</body>
</html>
"""


# --- Core Scanner Logic (from admin_finder.py) ---

def get_wordlist():
    """Reads and returns the list of paths from the wordlist file."""
    try:
        with open(WORDLIST_PATH, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Error: Wordlist file not found at '{WORDLIST_PATH}'")
        return []

def check_url(base_url, path):
    """Checks a single URL path for a valid response."""
    full_url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        headers = {'User-Agent': USER_AGENT}
        response = requests.get(full_url, headers=headers, timeout=TIMEOUT, allow_redirects=True)
        if response.status_code == 200:
            return {'url': full_url, 'status': response.status_code}
    except requests.RequestException:
        pass
    return None

def run_scan(target_url):
    """Runs the scan on the target URL and returns a list of found panels."""
    wordlist = get_wordlist()
    if not wordlist:
        return []

    found_panels = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        future_to_url = {executor.submit(check_url, target_url, path): path for path in wordlist}
        for future in as_completed(future_to_url):
            result = future.result()
            if result:
                found_panels.append(result)
    return sorted(found_panels, key=lambda x: x['url'])


# --- Flask Web Application ---

app = Flask(__name__)
# It's important to set a secret key for flashing messages
app.secret_key = 'a_random_secret_key_for_production' 

@app.route('/')
def index():
    """Renders the main page."""
    return render_template_string(INDEX_TEMPLATE)

@app.route('/scan', methods=['POST'])
def scan():
    """Handles the form submission and displays results."""
    url = request.form.get('url')
    if not url:
        flash('URL is required!', 'error')
        return render_template_string(INDEX_TEMPLATE)
    
    # Basic URL validation
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url

    try:
        # Check if the base URL is even reachable
        requests.get(url, timeout=TIMEOUT, headers={'User-Agent': USER_AGENT})
    except requests.RequestException:
        flash(f"Error: Could not connect to {url}. Please check the URL and try again.", 'error')
        return render_template_string(INDEX_TEMPLATE)

    found_panels = run_scan(url)
    return render_template_string(RESULTS_TEMPLATE, found_panels=found_panels, target_url=url)

if __name__ == '__main__':
    # This part is for local testing and won't be used by Gunicorn on Render
    app.run(host='0.0.0.0', port=5000, debug=True)
