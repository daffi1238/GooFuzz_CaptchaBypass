#!/usr/bin/env python3
import argparse
import os
import sys
import time
import urllib.parse
from typing import Optional, List
import re  # al principio del archivo



from DrissionPage import ChromiumPage
from RecaptchaSolver import RecaptchaSolver


BANNER = r"""
*********************************************************
* GooFuzz-browser - Google Dorks with real browser      *
*********************************************************
"""

def sanitize_for_filename(text: str, max_len: int = 80) -> str:
    """Return a filesystem-safe chunk derived from text."""
    # Replace non-alphanumeric chars by underscores
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "_", text)
    # Collapse multiple underscores
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
    Detects Recaptcha or Google temporary ban page.
    If detected, try solver. If solver fails, allow manual solving.
    """
    html = page.html.lower()

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
            time.sleep(5)
        except Exception as e:
            print(f"[!] Recaptcha solving failed: {e}", file=sys.stderr)

            #  ⬇️⬇️  AÑADE ESTE BLOQUE  ⬇️⬇️
            input(
                "\n⚠️ Google muestra un CAPTCHA.\n"
                "Resuélvelo manualmente en la ventana del navegador.\n"
                "Cuando hayas terminado, pulsa ENTER para continuar...\n"
            )

def extract_links_from_results(
    page: ChromiumPage,
    target: str,
    filetype: str = None,
    engine: str = "google",
) -> list:
    """
    Parse the search results page in the browser and extract relevant links.

    We:
        - use different selectors per search engine
        - fall back to generic <a> selection if needed
        - filter by target domain
        - optionally filter by filetype extension
    """
    links = []
    engine = (engine or "google").lower()

    try:
        # Engine-specific selectors for organic results
        if engine == "google":
            # Typical Google desktop organic results
            result_anchors = page.eles("css: div.yuRUbf a")
            if not result_anchors:
                result_anchors = page.eles("css: #search a")

        elif engine == "bing":
            # Bing organic results usually under li.b_algo h2 a
            result_anchors = page.eles("css: li.b_algo h2 a")
            if not result_anchors:
                result_anchors = page.eles("css: #b_results a")

        elif engine == "yandex":
            # Yandex SERP results anchors
            result_anchors = page.eles("css: .serp-item a[href]")
            if not result_anchors:
                result_anchors = page.eles("css: a.Link[href]")

        elif engine == "duckduckgo":
            # DuckDuckGo: result__a is main result title link
            result_anchors = page.eles("css: a.result__a")
            if not result_anchors:
                result_anchors = page.eles("css: #links a[href]")

        elif engine == "brave":
            # Brave Search: result title anchor
            result_anchors = page.eles("css: a[data-testid='result-title-a']")
            if not result_anchors:
                # Fallback to main results container links
                result_anchors = page.eles("css: main a[href]")

        else:
            # Unknown engine: pick any link in the document as a fallback
            result_anchors = page.eles("css: a[href]")

        # Final generic fallback if all of the above fail
        if not result_anchors:
            result_anchors = page.eles("css: a[href]")

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

        # Basic filters to remove junk
        # NOTE: We keep this generic; you may want to tune per engine if needed.
        if "google." in href:
            # Skip Google own URLs (cache, translate, etc.)
            continue
        if "bing.com" in href and "q=" in href and "redirect" in href:
            # Example: skip Bing redirector URLs if you see them
            continue

        if not href.startswith("http"):
            continue

        # Filter by target domain
        if target_lower not in href.lower():
            continue

        # Optional filetype filter
        if filetype:
            ext = filetype.lower()
            href_lower = href.lower()

            # Simple check: URL ends with ".ext"
            if not href_lower.endswith("." + ext):
                # Still allow if the URL contains ".ext" somewhere
                if f".{ext}" not in href_lower:
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
    keep_open: bool = False,
    engines: Optional[List[str]] = None,
    save_html_dir: Optional[str] = None,
):
    print(BANNER)

    if not engines:
        engines = ["google"]

    # Create dir for HTMLs if requested
    if save_html_dir:
        os.makedirs(save_html_dir, exist_ok=True)

    # TODO: headless/user_agent handling could be plugged in ChromiumPage options here.
    browser = ChromiumPage()
    solver = RecaptchaSolver(browser)

    # One tab per search engine
    engine_tabs = {}
    first_engine = True
    for engine in engines:
        if first_engine:
            # Use main page object for the first engine
            engine_tabs[engine] = browser
            first_engine = False
        else:
            # Create a new tab and activate it
            tab = browser.new_tab()
            try:
                # Important: activate this tab so .get() works on it
                tab.set.activate()
            except Exception:
                # Some versions/objects may not have set.activate()
                pass
            engine_tabs[engine] = tab

    # Global containers
    all_results_for_output = []          # All links found (for global output_file)
    seen_links = set()                  # Global dedup across engines and phases
    urls_by_engine = {eng: [] for eng in engines}  # Per-engine storage

    try:
        # ---------- Automatic dork-based scraping phase ----------
        for engine in engines:
            print(f"\n########## Using search engine: {engine} ##########\n")

            # Select the tab dedicated to this engine
            page_obj = engine_tabs[engine]

            for label, query in queries:
                print(f"\n===================================================================")
                print(f"Target: {target}")
                print(f"Engine: {engine}")
                print(f"Query label: {label}")
                print(f"Dork: {query}")
                print(f"===================================================================")

                # Build a safe chunk for filenames
                label_safe = sanitize_for_filename(str(label)) if label else "nolabel"
                query_safe = sanitize_for_filename(query)

                for page_idx in range(pages):
                    url = build_search_url_for_engine(engine, query, page_idx)
                    print(f"[+] [{engine}] Opening page {page_idx + 1}/{pages} -> {url}")
                    page_obj.get(url)
                    
                    # 🔴 ESPERA ACTIVA: Asegurar que la página esté completamente cargada
                    max_wait = 30  # Timeout máximo de espera
                    wait_start = time.time()
                    
                    while True:
                        elapsed = time.time() - wait_start
                        if elapsed > max_wait:
                            print(f"[!] Timeout esperando carga completa de página ({max_wait}s)")
                            break
                            
                        # Verificar que el DOM esté listo
                        try:
                            # Intentar extraer elementos, si falla es que no está listo
                            test_elements = page_obj.eles("css: body")
                            if test_elements:
                                print(f"[+] Página cargada correctamente ({elapsed:.1f}s)")
                                break
                        except Exception:
                            pass
                            
                        time.sleep(0.5)  # Pequeña pausa antes de reintentar
                    
                    # 🔴 RESOLVER CAPTCHA ANTES DE EXTRAER
                    maybe_solve_recaptcha(page_obj, solver)
                    
                    # 🔴 SEGUNDA VERIFICACIÓN: DOM post-CAPTCHA
                    time.sleep(2)  # Dar tiempo al DOM a actualizarse tras resolver CAPTCHA
                    
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
                    
                    # Decide filetype filter
                    filetype = (
                        label
                        if label
                        and "." not in label
                        and label not in ("subdomains", query)
                        else None
                    )
                    
                    # 🔴 EXTRACCIÓN GARANTIZADA: No avanzar hasta tener resultado
                    extraction_attempts = 0
                    max_attempts = 3
                    links = []
                    
                    while extraction_attempts < max_attempts:
                        extraction_attempts += 1
                        print(f"[+] Intento de extracción {extraction_attempts}/{max_attempts}...")
                        
                        links = extract_links_from_results(
                            page=page_obj,
                            target=target,
                            filetype=filetype,
                            engine=engine,
                        )
                        
                        if links:
                            print(f"[+] ✓ Extraídas {len(links)} URLs exitosamente")
                            break
                        else:
                            print(f"[-] No se encontraron links en intento {extraction_attempts}")
                            if extraction_attempts < max_attempts:
                                print(f"    Esperando 3s antes de reintentar...")
                                time.sleep(3)
                    
                    # 🔴 VERIFICACIÓN FINAL
                    if not links:
                        print("[-] ⚠️ No se pudieron extraer URLs tras múltiples intentos")
                        print("    Considera que puede ser:")
                        print("    - Fin de resultados")
                        print("    - CAPTCHA no resuelto")
                        print("    - Cambio en estructura HTML del buscador")
                        
                        # Opcional: pausa para inspección manual
                        user_choice = input("    ¿Continuar de todos modos? (s/N): ").strip().lower()
                        if user_choice != 's':
                            print("    Deteniendo búsqueda en este motor...")
                            break
                    
                    # Procesar links encontrados
                    new_links = [link for link in links if link not in seen_links]
                    
                    for link in new_links:
                        seen_links.add(link)
                        print(link)
                        all_results_for_output.append(link)
                        urls_by_engine[engine].append(link)
                    
                    # Escribir en tiempo real
                    if new_links:
                        engine_filename = f"url_{engine}.txt"
                        try:
                            with open(engine_filename, "a", encoding="utf-8") as f:
                                for link in new_links:
                                    f.write(link + "\n")
                        except Exception as e:
                            print(f"[!] Failed to write to {engine_filename}: {e}", file=sys.stderr)
                    
                    # 🔴 DELAY SOLO DESPUÉS DE PROCESAR TODO
                    if delay > 0 and page_idx < pages - 1:  # No delay en última página
                        print(f"[+] Esperando {delay}s antes de siguiente página...")
                        time.sleep(delay)

        # ---------- Realtime monitoring phase ----------
        if keep_open:
            print("\n[+] Automatic phase finished.")
            print("[+] Entering realtime monitoring mode (manual browsing + auto-scraping).")
            monitor_tabs_realtime(
                engine_tabs=engine_tabs,
                target=target,
                seen_links=seen_links,
                all_results_for_output=all_results_for_output,
                urls_by_engine=urls_by_engine,
                output_file=output_file,    # Currently not writing per-link in realtime
                poll_interval=5.0,          # Adjust interval as needed
            )

    finally:
        # Only close the browser if explicitly requested
        if not keep_open:
            browser.close()
        else:
            print("[*] keep_open=True -> not closing browser from script.")
            print("    When Python process exits, browser will normally close as well.")

    # -------- Save per-engine URL files at the end --------
    print("\n[+] Saving per-engine URL files...")

    for eng, links in urls_by_engine.items():
        if not links:
            print(f"[-] No links found for {eng}, skipping file.")
            continue

        # Deduplicate preserving order
        unique = []
        seen_local = set()
        for link in links:
            if link not in seen_local:
                seen_local.add(link)
                unique.append(link)

        filename = f"url_{eng}.txt"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                for l in unique:
                    f.write(l + "\n")
            print(f"[+] Saved {len(unique)} links to: {filename}")
        except Exception as e:
            print(f"[!] Error writing {filename}: {e}")

    # -------- Global output file (if requested) --------
    if output_file and all_results_for_output:
        try:
            with open(output_file, "a", encoding="utf-8") as f:
                for link in all_results_for_output:
                    f.write(link + "\n")
            print(f"\n[+] Results appended to: {output_file}")
        except Exception as e:
            print(f"[!] Error writing global output file {output_file}: {e}")




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

    # NEW: search engine selection
    parser.add_argument(
        "--engine",
        default="google",
        choices=["google", "bing", "yandex", "duckduckgo", "brave", "all"],
        help="Search engine to use (default: google). Use 'all' to query all supported engines."
    )
    # to save html of the interactive browser session
    parser.add_argument(
        "--save-html-dir",
        help="Directory to store raw HTML result pages for offline analysis",
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

    return parser.parse_args()


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
        # 'first' es el índice (1-based) del primer resultado en esa página
        base_url = "https://www.bing.com/search?q="
        first = page_num * 10 + 1  # 1,11,21,...
        return f"{base_url}{encoded_q}&first={first}"

    # Yandex
    if engine == "yandex":
        # 'p' es el índice de página empezando en 0
        base_url = "https://yandex.com/search/?text="
        return f"{base_url}{encoded_q}&p={page_num}"

    # DuckDuckGo (versión HTML, sin JS)
    if engine == "duckduckgo":
        base_url = "https://html.duckduckgo.com/html/?q="
        if page_num == 0:
            return f"{base_url}{encoded_q}"
        # Paginación básica: s=offset, dc=doc count approx
        offset = page_num * 30
        dc = offset + 1
        return f"{base_url}{encoded_q}&s={offset}&dc={dc}"

    # Brave
    if engine == "brave":
        # Brave usa 'offset' para paginación
        base_url = "https://search.brave.com/search?q="
        offset = page_num  # 0,1,2,... (Brave se encarga del tamaño de página)
        return f"{base_url}{encoded_q}&offset={offset}"

    # Fallback si alguien mete algo raro
    raise ValueError(f"Unsupported search engine: {engine}")


def monitor_tabs_realtime(
    engine_tabs: dict,
    target: str,
    seen_links: set,
    all_results_for_output: list,
    urls_by_engine: dict,
    output_file: Optional[str] = None,
    poll_interval: float = 2.0,
):
    """
    Continuously monitor each engine tab and extract links in "near real-time".

    - Periodically runs extract_links_from_results() on each tab.
    - Prints and records only *new* links (using seen_links set).
    - Appends new links to per-engine storage (urls_by_engine).
    - Optionally can be extended to write to a global output file.

    User can keep manually browsing (new searches, next pages, etc.).
    Stop with Ctrl+C in the terminal.
    """
    print("\n[Realtime] Starting live monitoring of all tabs.")
    print("          You can manually browse in the browser.")
    print("          Press Ctrl+C in this terminal to stop realtime mode.\n")

    try:
        while True:
            for engine, page_obj in engine_tabs.items():
                try:
                    links = extract_links_from_results(
                        page=page_obj,
                        target=target,
                        filetype=None,   # In realtime mode, ignore filetype filter; adjust if needed
                        engine=engine,
                    )
                except Exception as e:
                    print(f"[!] Error extracting links from {engine} tab: {e}", file=sys.stderr)
                    continue

                new_links = [link for link in links if link not in seen_links]
                if not new_links:
                    continue

                print(f"\n[+] {len(new_links)} new link(s) found in {engine} tab:")
                for link in new_links:
                    seen_links.add(link)
                    all_results_for_output.append(link)
                    urls_by_engine[engine].append(link)
                    print(link)

                    # If you ever want to write to a global output_file in realtime,
                    # you can do it here. For now we keep "only at the end" logic.

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print("\n[Realtime] Monitoring stopped by user (Ctrl+C).")



def main():
    args = parse_args()

    target = args.target
    pages = max(args.pages, 1)
    delay = max(args.delay, 0.0)

    if args.engine == "all":
        engines = ["google", "bing", "yandex", "duckduckgo", "brave"]
    else:
        engines = [args.engine]

    if args.raw:
        queries = [("raw", args.raw)]
    else:
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

    # Run automated queries
    run_query_with_browser(
        queries=queries,
        target=target,
        pages=pages,
        delay=delay,
        output_file=args.output,
        headless=args.headless,
        user_agent=args.user_agent,
        engines=engines,
        keep_open=True,              # <--- do not close browser in finally
        save_html_dir=args.save_html_dir,
    )

    # 🔴 IMPORTANT: keep the process alive so Chromium stays open
    input(
        "\n[+] Finished automated queries.\n"
        "You can now freely navigate in the browser window.\n"
        "When you are done and want to close everything, press ENTER here...\n"
    )


if __name__ == "__main__":
    main()
