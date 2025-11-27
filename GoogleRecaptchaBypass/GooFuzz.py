#!/usr/bin/env python3
import argparse
import os
import sys
import time
import urllib.parse

from DrissionPage import ChromiumPage
from RecaptchaSolver import RecaptchaSolver


BANNER = r"""
*********************************************************
* GooFuzz-browser - Google Dorks with real browser      *
*********************************************************
"""


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
    GooFuzz uses an OR-like pattern; here we just do inurl:"w1|w2|w3"
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

    # e.g. inurl:"admin|config|backup"
    return f'inurl:"{"|".join(words)}"'


def build_contents(contents: str) -> str:
    """
    Build search for content inside files.
    Original GooFuzz uses infile:"a"||"b" pattern.
    Here we stick close to that idea, but you can change it to intext: if you prefer.
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

    # infile:"pass"||"secret"
    # NOTE: Google-style dork; you may tweak this to intext: or similar
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
        - query: actual Google query string WITHOUT url-encoding.
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
        # e.g. site:*.target -site:www.target
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


def build_search_url(query: str, page_num: int, filter_flag: bool = False) -> str:
    """
    Build the final Google search URL for a given query and page number.
    filter_flag mimics the &filter=0 option of GooFuzz.
    """
    base_url = "https://www.google.com/search?q="
    encoded_q = urllib.parse.quote_plus(query)
    # page_num is 0,1,2,... but Google expects start=0,10,20,...
    start = page_num * 10
    url = f"{base_url}{encoded_q}&start={start}"
    if not filter_flag:
        # GooFuzz uses &filter=0 to avoid "similar results" filtering
        url += "&filter=0"
    return url


def maybe_solve_recaptcha(page: ChromiumPage, solver: RecaptchaSolver):
    """
    Best-effort detection of Recaptcha / Google temporary ban page.
    If detected, call RecaptchaSolver.
    You can refine this logic based on what Google actually returns in your region.
    """
    html = page.html.lower()

    # Very rough checks – you can tune this with more precise selectors
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
            # Give some time for page to reload
            time.sleep(5)
        except Exception as e:
            print(f"[!] Recaptcha solving failed: {e}", file=sys.stderr)


def extract_links_from_results(page: ChromiumPage, target: str, filetype: str = None) -> list:
    """
    Parse the Google results page in the browser and extract relevant links.

    NOTE: Google changes HTML structure frequently.
    This function uses typical selectors, but you may need to adjust.

    We:
        - look for organic result links
        - filter by target domain
        - optionally filter by filetype extension
    """
    links = []

    # Typical organic result selector (desktop):
    #   div.yuRUbf > a
    # But we add fallback to any link inside #search.
    try:
        result_anchors = page.eles("css: div.yuRUbf a")
        if not result_anchors:
            # Fallback selector
            result_anchors = page.eles("css: #search a")
    except Exception:
        result_anchors = []

    target_lower = target.lower()

    for a in result_anchors:
        try:
            href = a.attr("href")
        except Exception:
            href = None

        if not href:
            continue

        # Basic filters to remove Google junk
        if "google." in href:
            continue
        if not href.startswith("http"):
            continue

        if target_lower not in href.lower():
            continue

        if filetype:
            # Simple check, e.g. ".pdf" in URL
            if not href.lower().endswith("." + filetype.lower()):
                # Still allow if the URL contains ".ext" somewhere
                if f".{filetype.lower()}" not in href.lower():
                    continue

        links.append(href)

    # Deduplicate preserving order
    seen = set()
    unique_links = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique_links.append(link)

    return unique_links


def run_query_with_browser(
    queries: list,
    target: str,
    pages: int,
    delay: float,
    output_file: str = None,
    headless: bool = False,
    user_agent: str = None,
):
    """
    Main loop:
        - start ChromiumPage
        - for each (label, query) build URLs, paginate, solve recaptchas, parse results
        - print to stdout and optionally write to output file
    """
    print(BANNER)

    # Configure ChromiumPage
    # You can pass arguments or profile here if needed
    browser = ChromiumPage()
    solver = RecaptchaSolver(browser)

    all_results_for_output = []

    try:
        for label, query in queries:
            print(f"\n===================================================================")
            print(f"Target: {target}")
            print(f"Query label: {label}")
            print(f"Dork: {query}")
            print(f"===================================================================")

            for page_idx in range(pages):
                url = build_search_url(query, page_idx)
                print(f"[+] Opening page {page_idx + 1}/{pages} -> {url}")
                browser.get(url)
                time.sleep(2)

                # Check if we hit a ban / recaptcha
                maybe_solve_recaptcha(browser, solver)

                # Extract links
                # In extension mode, label is extension, otherwise we don't filter.
                filetype = label if label and "." not in label and label not in ("subdomains", query) else None
                links = extract_links_from_results(browser, target, filetype=filetype)

                if not links:
                    print("[-] No more results found on this page.")
                    break

                for link in links:
                    print(link)
                    all_results_for_output.append(link)

                if delay > 0:
                    time.sleep(delay)

        if output_file and all_results_for_output:
            with open(output_file, "a", encoding="utf-8") as f:
                for link in all_results_for_output:
                    f.write(link + "\n")
            print(f"\n[+] Results appended to: {output_file}")

    finally:
        browser.close()


def parse_args():
    """
    Argument parser roughly compatible with GooFuzz logic, but simplified.
    """
    parser = argparse.ArgumentParser(
        description="GooFuzz-browser: Google dorks using a real Chromium browser + RecaptchaSolver"
    )

    parser.add_argument("-t", "--target", required=True, help="Target domain (site.com)")
    parser.add_argument("-p", "--pages", type=int, default=1, help="Number of result pages to fetch")
    parser.add_argument("-d", "--delay", type=float, default=1.0, help="Delay (seconds) between page requests")
    parser.add_argument("-o", "--output", help="Output file for results (append mode)")
    parser.add_argument("-x", "--exclusions", help="Exclusions: file or comma-separated domains")
    parser.add_argument("-r", "--raw", help="Raw dork (if set, other mode flags are ignored)")

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

    return parser.parse_args()


def main():
    args = parse_args()

    target = args.target
    pages = max(args.pages, 1)
    delay = max(args.delay, 0.0)

    # If user provides a raw dork, just use that directly.
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
        output_file=args.output,
        headless=args.headless,
        user_agent=args.user_agent,
    )


if __name__ == "__main__":
    main()
