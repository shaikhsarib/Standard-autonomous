"""
Scrapling Live Research Utility
Leverages D4Vinci/Scrapling with curl_cffi and browserforge to scrape, bypass anti-bots,
and extract clean Markdown for UI/UX analysis and prospect audits.
"""

import sys
from scrapling.fetchers import Fetcher

def research_url(url: str) -> dict:
    try:
        response = Fetcher.get(url, timeout=15)
        markdown_content = ""
        try:
            markdown_content = response.markdown()
        except Exception:
            markdown_content = response.body.decode('utf-8', errors='ignore')
            
        return {
            "status": response.status,
            "url": url,
            "length": len(response.body),
            "markdown": markdown_content
        }
    except Exception as e:
        return {
            "error": str(e),
            "url": url
        }

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "https://opensourceui.in/components/arc-bands-background"
    print(f"[*] Researching live: {target}")
    result = research_url(target)
    if "error" in result:
        print(f"[!] Error: {result['error']}")
    else:
        print(f"[+] Status: {result['status']} | Length: {result['length']} bytes")
        print("\n--- Markdown Snippet ---\n")
        print(result["markdown"][:600])
