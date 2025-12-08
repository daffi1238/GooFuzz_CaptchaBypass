Added functionality for GooFuzz to Get-Cookie from selenium Browser. 

Help to bypass Google restriction somehow.


```bash
source ~/enum_venv39/bin/activate
pip install DrissionPage
pip install SpeechRecognition
```

## 📌 GooFuzz-Browser 

Crawler multi-motor basado en navegador real + análisis offline de endpoints

Este proyecto permite lanzar Google dorks y consultas equivalentes en varios motores de búsqueda (Google, Bing, Yandex, DuckDuckGo, Brave) usando un navegador Chromium real mediante DrissionPage.
El objetivo es:

1.Indexar contenido específico usando dorks.
2. Guardar todos los HTML crudos (sin extracción online).
3. Analizar offline esos HTML para extraer:
    - URLs completas
    - Subdominios
    - Endpoints
    - Parámetros
    - Extensiones

🚀 Características

Un solo navegador con varias pestañas, una por motor de búsqueda.
Compatible con:
- Google
- Bing
- Yandex
- DuckDuckGo (HTML mode)
- Brave Search

Construye automáticamente dorks:
- inurl
- filetype
- infile
- subdomains

Guarda TODOS los HTML generados (--save-html-dir).
Pensado para análisis forense, OSINT, pentesting y exploración con bajo footprint online.
El análisis de enlaces se hace offline con regex en Linux o con scripts adicionales.

```bash
# estructura
+ goofuzz_browser_simplified.py     → crawler (navegador real)
+ html_sessions/                    → HTML crudos guardados
+ analysis/                         → scripts opcionales de análisis offline
```


## Uso
```
git clone https://github.com/daffi1238/GooFuzz_CaptchaBypass
cd ./GooFuzz_CaptchaBypass/GoogleRecaptchaBypass

source ~/enum_venv39/bin/activate
pip install -r requirements.txt


########################## Examples ############################
python3 GooFuzz.py  -t tesla.com -s --engine all
python3 GooFuzz.py  -t tesla.com -e pdf --engine all

########################## Results  #############################
# subdomains
cat url_* | grep -Ev "www\.bing\.com|yandex.com|duckduckgo.com" | grep -oP 'https?:\/\/\K([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)'  | sort -u


# extensions
cat ../wordlists/common-extensions.txt | xargs -I {} zsh -c 'timeout 90 python3 GooFuzz.py  -t tesla.com -e {} --engine all'

cat ../wordlists/common-extensions.txt | xargs -I {} zsh -c 'timeout 90 python3 GooFuzz.py  -t tesla.com -e {}'

cat ../wordlists/common-extensions.txt | xargs -I {} zsh -c 'timeout 30 python3 GooFuzz.py  -t tesla.com -w {}'
```

