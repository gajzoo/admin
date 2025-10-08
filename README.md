# AdminFinder-Pro

⚡ Advanced Admin Panel Finder with async scanning, stealth, and JSON reporting.

## Features
- Async fast scanner
- 1000+ common admin paths
- Detects login/admin panels
- Random User-Agent rotation
- Proxy support
- JSON results

## Usage
```bash
pip install -r requirements.txt

# Basic scan
python3 admin_finder.py https://example.com

# Fast scan with 30 threads
python3 admin_finder.py https://example.com -t 30

# With proxy
python3 admin_finder.py https://example.com --proxy http://127.0.0.1:8080
