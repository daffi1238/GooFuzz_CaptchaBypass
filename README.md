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

```