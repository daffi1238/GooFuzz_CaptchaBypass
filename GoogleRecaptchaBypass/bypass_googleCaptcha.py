from DrissionPage import ChromiumPage, ChromiumOptions
from RecaptchaSolver import RecaptchaSolver
import time
import sys

# URL y User-Agent pasados como parámetro
url = sys.argv[1]
user_agent = sys.argv[2]
print(url)
print(user_agent)

# Configurar las opciones de Chromium
options = ChromiumOptions()
options.set_user_agent(user_agent)

# Inicializar el driver y el resolver de reCAPTCHA
driver = ChromiumPage(addr_or_opts=options)
recaptchaSolver = RecaptchaSolver(driver)

# Navegar a la URL e intentar resolver el CAPTCHA (best-effort)
driver.get(url)
t0 = time.time()
recaptchaSolver.solveCaptcha()
print(f"Time to solve the captcha: {time.time() - t0:.2f} seconds")

# Mantener el navegador abierto para resolución manual; se cierra con Enter.
input("\n[!] Resuelve el CAPTCHA en el navegador y pulsa Enter para cerrar...\n")

driver.close()
print("Navegador cerrado.")
