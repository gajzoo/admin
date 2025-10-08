#!/usr/bin/env python3
import argparse
import requests
import concurrent.futures
import random
import json
import csv
import os
from urllib.parse import urljoin
from rich.console import Console
from rich.table import Table

console = Console()

# Common user agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Mozilla/5.0 (X11; Linux x86_64)",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_2 like Mac OS X)",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"
]

def load_wordlist(wordlist_file):
    if not os.path.exists(wordlist_file):
        console.print(f"[red]❌ Wordlist file not found: {wordlist_file}[/red]")
        return []
    with open(wordlist_file, "r") as f:
        return [line.strip() for line in f if line.strip()]

def check_url(base_url, path, timeout, proxy):
    url = urljoin(base_url, path)
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, proxies=proxy, allow_redirects=False)
        return url, resp.status_code, len(resp.content)
    except requests.RequestException:
        return url, None, 0

def scan_admin_panels(base_url, wordlist, threads, timeout, proxy):
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        future_to_url = {executor.submit(check_url, base_url, path, timeout, proxy): path for path in wordlist}
        for future in concurrent.futures.as_completed(future_to_url):
            url, status, size = future.result()
            if status in [200, 301, 302, 401, 403]:
                console.print(f"[green]✅ Found: {url} (Status: {status}, Size: {size})[/green]")
                results.append({"url": url, "status": status, "size": size})
            else:
                console.print(f"[yellow]⚠ Scanned: {url} (Status: {status})[/yellow]")
    return results

def save_results(results, output_file, output_format):
    if output_format == "txt":
        with open(output_file, "w") as f:
            for r in results:
                f.write(f"{r['url']} - {r['status']} - {r['size']}\n")
    elif output_format == "json":
        with open(output_file, "w") as f:
            json.dump(results, f, indent=4)
    elif output_format == "csv":
        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "status", "size"])
            writer.writeheader()
            writer.writerows(results)

def main():
    parser = argparse.ArgumentParser(description="Admin Panel Finder Pro")
    parser.add_argument("target", help="Target URL (e.g., https://example.com/)")
    parser.add_argument("-w", "--wordlist", default="admin_wordlist.txt", help="Wordlist file")
    parser.add_argument("-t", "--threads", type=int, default=10, help="Number of threads (default: 10)")
    parser.add_argument("--timeout", type=int, default=10, help="Request timeout (default: 10s)")
    parser.add_argument("--proxy", help="Proxy (e.g., http://127.0.0.1:8080)")
    parser.add_argument("-o", "--output", help="Save results to file")
    parser.add_argument("--format", choices=["txt", "json", "csv"], default="txt", help="Output format (default: txt)")
    args = parser.parse_args()

    base_url = args.target if args.target.endswith("/") else args.target + "/"
    proxy = {"http": args.proxy, "https": args.proxy} if args.proxy else None

    wordlist = load_wordlist(args.wordlist)
    if not wordlist:
        console.print("[red]No wordlist loaded. Exiting.[/red]")
        return

    console.print(f"[cyan]🚀 Starting scan on {base_url} with {args.threads} threads[/cyan]")
    results = scan_admin_panels(base_url, wordlist, args.threads, args.timeout, proxy)

    if args.output:
        save_results(results, args.output, args.format)
        console.print(f"[blue]💾 Results saved to {args.output} ({args.format})[/blue]")

    # Display results in table
    if results:
        table = Table(title="Admin Finder Results")
        table.add_column("URL", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Size", style="magenta")
        for r in results:
            table.add_row(r["url"], str(r["status"]), str(r["size"]))
        console.print(table)
    else:
        console.print("[red]❌ No admin panels found.[/red]")

if __name__ == "__main__":
    main()
