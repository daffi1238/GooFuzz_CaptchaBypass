#!/usr/bin/env python3
import argparse
import os
import sys
import time
import urllib.parse
import re
from typing import Optional, List

from DrissionPage import ChromiumPage
from RecaptchaSolver import RecaptchaSolver


BANNER = r"""
*********************************************************
* GooFuzz-browser - Google Dorks with real browser      *
* Simplified: multi-engine + save all HTML              *
*********************************************************
"""


def sanitize_for_filename(text: str, max_len: int = 80) -> str:
    """
    Make a text safe to be used as part of a filename.
    - Replace non-alphanumeric chars by underscores.
    - Limit to max_len characters.
    """
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", text)
    safe = re.sub(r"_+", "_", safe).strip("_")
    if len(safe) > max_len:
        safe = safe[:max_len]
    if not safe:
        safe = "query"
    return safe


def build_exclusions(exclusions: str) -> str:
    """
    Build the -site: exclusions part for Google query.
    Accepts:
        - a file path with domains (one per line)
        - a comma-separated list: "dev.site.com,pre.site.com"
        - single domain
    Returns something like: -site:dev.site.com -site:pre.site.com
    """
    if not exclusions:
        return ""

    exclude_targets = []

    # File with exclusion list
    if os.path.isfile(exclusions):
        with open(exclusions, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                domain = line.strip()
                if domain:
                    exclude_targets.append(f"-site:{domain}")

    # Comma-separated list
    elif "," in exclusions:
        for domain in exclusions.split(","):
            domain = domain.strip()
            if domain:
                exclude_targets.append(f"-site:{domain}")

    # Single domain
    else:
        exclude_targets.append(f"-site:{exclusions.strip()}")

    return " ".join(exclude_targets)


def build_inurl(dictionary: str) -> str:
    """
    Build the inurl: part using a dictionary.
    Accepts:
        - file with words (one per line)
        - "word1,word2" list
        - single word
    Returns e.g.: inurl:"admin|config|backup"
    """
    if not dictionary:
        return ""

    words = []

    if os.path.isfile(dictionary):
        with open(dictionary, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = line.strip()
                if w:
                    words.append(w)
    elif "," in dictionary:
        for w in dictionary.split(","):
            w = w.strip()
            if w:
                words.append(w)
    else:
        words.append(dictionary.strip())

    if not words:
        return ""

    return f'inurl:"{"|".join(words)}"'


def build_contents(contents: str) -> str:
    """
    Build search for content inside files.
    Accepts:
        - file with tokens (one per line)
        - "token1,token2" list
        - single token
    Returns GooFuzz-style infile pattern, e.g.:
        infile:"pass"||"secret"
    """
    if not contents:
        return ""

    tokens = []

    if os.path.isfile(contents):
        with open(contents, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                t = line.strip()
                if t:
                    tokens.append(t)
    elif "," in contents:
        for t in contents.split(","):
            t = t.strip()
            if t:
                tokens.append(t)
    else:
        tokens.append(contents.strip())

    if not tokens:
        return ""

    return 'infile:"' + '"||"'.join(tokens) + '"'


def build_extension_list(extension: str) -> list:
    """
    Normalize extension argument into a list.
    Accepts:
        - file with extensions
        - "pdf,doc" list
        - single extension
    """
    if not extension:
        return []

    exts = []

    if os.path.isfile(extension):
        with open(extension, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                e = line.strip().lstrip(".")
                if e:
                    exts.append(e)
    elif "," in extension:
        for e in extension.split(","):
            e = e.strip().lstrip(".")
            if e:
                exts.append(e)
    else:
        exts.append(extension.strip().lstrip("."))

    return exts


def build_query(
    target: str,
    mode: str,
    extension: str = None,
    dictionary: str = None,
    subdomain: bool = False,
    contents: str = None,
    exclusions: str = None,
) -> list:
    """
    Build one or multiple dork queries depending on the mode.
    Returns a list of tuples: [(label, query), ...]
        - label: what we’re looking for (e.g. "pdf", "subdomains", etc.)
        - query: actual search query string WITHOUT url-encoding.
    """
    queries = []
    base_target = target.strip()

    exclude_str = build_exclusions(exclusions)
    inurl_str = build_inurl(dictionary) if dictionary else ""
    contents_str = build_contents(contents) if contents else ""

    # Dictionary mode: site:target inurl:"..."
    if mode == "dictionary" and inurl_str:
        q = f"site:{base_target} {inurl_str}"
        if exclude_str:
            q += " " + exclude_str
        queries.append((dictionary, q))

    # Extension mode: possibly multiple filetypes
    elif mode == "extension":
        exts = build_extension_list(extension)
        for ext in exts:
            q = f"site:{base_target} filetype:{ext}"
            if contents_str:
                q += " " + contents_str
            if exclude_str:
                q += " " + exclude_str
            queries.append((ext, q))

    # Subdomain mode
    elif mode == "subdomain" and subdomain:
        # Typical subdomain enumeration dork
        q = f"site:*.{base_target} -site:www.{base_target}"
        if exclude_str:
            q += " " + exclude_str
        queries.append(("subdomains", q))

    # Contents mode: site:target infile:"..."
    elif mode == "contents" and contents_str:
        q = f"site:{base_target} {contents_str}"
        if exclude_str:
            q += " " + exclude_str
        queries.append((contents, q))

    return queries


def build_search_url_for_engine(engine: str, query: str, page_num: int, filter_flag: bool = False) -> str:
    """
    Build the search URL for the given engine, query and page number.
    page_num is 0,1,2,...

    filter_flag is only relevant for Google (&filter=0).
    """
    encoded_q = urllib.parse.quote_plus(query)

    # Google
    if engine == "google":
        base_url = "https://www.google.com/search?q="
        start = page_num * 10  # 0,10,20,...
        url = f"{base_url}{encoded_q}&start={start}"
        if not filter_flag:
            url += "&filter=0"
        return url

    # Bing
    if engine == "bing":
        # 'first' is the (1-based) index of the first result on this page
        base_url = "https://www.bing.com/search?q="
        first = page_num * 10 + 1  # 1,11,21,...
        return f"{base_url}{encoded_q}&first={first}"

    # Yandex
    if engine == "yandex":
        # 'p' is the page index starting from 0
        base_url = "https://yandex.com/search/?text="
        return f"{base_url}{encoded_q}&p={page_num}"

    # DuckDuckGo (HTML version)
    if engine == "duckduckgo":
        base_url = "https://html.duckduckgo.com/html/?q="
        if page_num == 0:
            return f"{base_url}{encoded_q}"
        # Basic pagination: s=offset, dc=doc count approx
        offset = page_num * 30
        dc = offset + 1
        return f"{base_url}{encoded_q}&s={offset}&dc={dc}"

    # Brave
    if engine == "brave":
        # Brave uses 'offset' for pagination
        base_url = "https://search.brave.com/search?q="
        offset = page_num  # 0,1,2,... (Brave handles page size)
        return f"{base_url}{encoded_q}&offset={offset}"

    raise ValueError(f"Unsupported search engine: {engine}")


def maybe_solve_recaptcha(page: ChromiumPage, solver: RecaptchaSolver):
    """
    Best-effort detection of Recaptcha / temporary ban page.
    If detected, call RecaptchaSolver.
    """
    try:
        html = page.html.lower()
    except Exception:
        return

    ban_signatures = [
        "our systems have detected unusual traffic",
        "to continue, please type the characters below",
        "recaptcha",
        "unusual traffic from your computer network",
    ]

    if any(sig in html for sig in ban_signatures):
        print("[!] Detected Google ban / Recaptcha. Trying to solve it...")
        try:
            solver.solveCaptcha()
            time.sleep(5)  # wait for page to reload
        except Exception as e:
            print(f"[!] Recaptcha solving failed: {e}", file=sys.stderr)


def run_query_with_browser(
    queries: list,
    target: str,
    pages: int,
    delay: float,
    headless: bool = False,
    user_agent: str = None,
    engines: Optional[List[str]] = None,
    save_html_dir: Optional[str] = None,
):
    """
    Main routine:
    - Start a single Chromium browser.
    - Open one tab per search engine.
    - For each query and page, open the search URL and save the HTML.
    """
    print(BANNER)

    if not engines:
        engines = ["google"]

    # Create directory for HTML dumps if requested
    if save_html_dir:
        os.makedirs(save_html_dir, exist_ok=True)

    # Initialize browser (NOTE: headless / UA setup should be done via DrissionPage config)
    browser = ChromiumPage()
    solver = RecaptchaSolver(browser)

    # Map: engine -> tab/page object
    engine_tabs = {}
    first_engine = True
    for engine in engines:
        if first_engine:
            # Use the main page for the first engine
            engine_tabs[engine] = browser
            first_engine = False
        else:
            # Create a new tab for each additional engine
            tab = browser.new_tab()
            engine_tabs[engine] = tab

    try:
        for engine in engines:
            print(f"\n########## Using search engine: {engine} ##########\n")

            page_obj = engine_tabs[engine]

            for label, query in queries:
                print("\n===================================================================")
                print(f"Target: {target}")
                print(f"Engine: {engine}")
                print(f"Query label: {label}")
                print(f"Dork: {query}")
                print("===================================================================")

                label_safe = sanitize_for_filename(str(label)) if label else "nolabel"
                query_safe = sanitize_for_filename(query)

                for page_idx in range(pages):
                    url = build_search_url_for_engine(engine, query, page_idx)
                    print(f"[+] [{engine}] Opening page {page_idx + 1}/{pages} -> {url}")
                    page_obj.get(url)
                    time.sleep(2)

                    # Try to handle Recaptcha / temporary bans
                    maybe_solve_recaptcha(page_obj, solver)

                    # Save raw HTML if requested
                    if save_html_dir:
                        filename = f"{engine}_{label_safe}_p{page_idx + 1}_{query_safe}.html"
                        filepath = os.path.join(save_html_dir, filename)
                        try:
                            html_content = page_obj.html
                            with open(filepath, "w", encoding="utf-8") as f:
                                f.write(html_content)
                            print(f"[+] Saved HTML to {filepath}")
                        except Exception as e:
                            print(f"[!] Failed to save HTML to {filepath}: {e}", file=sys.stderr)

                    if delay > 0:
                        time.sleep(delay)

    finally:
        browser.close()


def parse_args():
    """
    Argument parser roughly compatible with GooFuzz logic, simplified.
    """
    parser = argparse.ArgumentParser(
        description="GooFuzz-browser (simplified): multi-engine dorks using a real Chromium browser, saving all HTML."
    )

    parser.add_argument("-t", "--target", required=True, help="Target domain (site.com)")
    parser.add_argument("-p", "--pages", type=int, default=1, help="Number of result pages to fetch per query/engine")
    parser.add_argument("-d", "--delay", type=float, default=1.0, help="Delay (seconds) between page requests")
    parser.add_argument("-x", "--exclusions", help="Exclusions: file or comma-separated domains")
    parser.add_argument("-r", "--raw", help="Raw dork (if set, other mode flags are ignored)")

    # Search engine selection
    parser.add_argument(
        "--engine",
        default="google",
        choices=["google", "bing", "yandex", "duckduckgo", "brave", "all"],
        help="Search engine to use (default: google). Use 'all' to query all supported engines."
    )

    # Modes (mutually exclusive)
    modes = parser.add_mutually_exclusive_group(required=False)
    modes.add_argument("-w", "--dictionary", help="Dictionary for inurl search (file or comma-separated)")
    modes.add_argument("-e", "--extension", help="Extensions for filetype search (file or comma-separated)")
    modes.add_argument("-s", "--subdomains", action="store_true", help="Search subdomains for target")
    modes.add_argument("-c", "--contents", help="Search contents in files (file or comma-separated)")

    parser.add_argument("--headless", action="store_true", help="Run Chromium in headless mode (if supported)")
    parser.add_argument(
        "--user-agent",
        help="Custom User-Agent for Chromium (you may need to set it via DrissionPage options manually)",
    )

    # Directory where HTML files will be stored
    parser.add_argument(
        "--save-html-dir",
        required=True,
        help="Directory to store raw HTML result pages for offline analysis",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    target = args.target
    pages = max(args.pages, 1)
    delay = max(args.delay, 0.0)

    # Normalize engine list
    if args.engine == "all":
        engines = ["google", "bing", "yandex", "duckduckgo", "brave"]
    else:
        engines = [args.engine]

    # If user provides a raw dork, use that directly.
    if args.raw:
        queries = [("raw", args.raw)]
    else:
        # Determine mode
        if args.dictionary:
            mode = "dictionary"
        elif args.extension:
            mode = "extension"
        elif args.subdomains:
            mode = "subdomain"
        elif args.contents:
            mode = "contents"
        else:
            print("[!] You must choose one mode: -w, -e, -s or -c (or use -r for raw dork)")
            sys.exit(1)

        queries = build_query(
            target=target,
            mode=mode,
            extension=args.extension,
            dictionary=args.dictionary,
            subdomain=args.subdomains,
            contents=args.contents,
            exclusions=args.exclusions,
        )

        if not queries:
            print("[!] No valid query could be built. Check your arguments.")
            sys.exit(1)

    run_query_with_browser(
        queries=queries,
        target=target,
        pages=pages,
        delay=delay,
        headless=args.headless,
        user_agent=args.user_agent,
        engines=engines,
        save_html_dir=args.save_html_dir,
    )


if __name__ == "__main__":
    main()
