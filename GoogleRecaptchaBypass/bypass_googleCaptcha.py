from DrissionPage import ChromiumPage, ChromiumOptions
from RecaptchaSolver import RecaptchaSolver
import time
import sys

# URL de ejemplo o pasada por parámetro
url = sys.argv[1]
user_agent = sys.argv[2]
print(url)
print(user_agent)

# Configurar las opciones de Chromium para incluir el User-Agent
options = ChromiumOptions()
options.set_argument(f"user-agent={user_agent}")

# Inicializar el driver y el resolver de reCAPTCHA con las opciones configuradas
driver = ChromiumPage(addr_or_opts=options)
recaptchaSolver = RecaptchaSolver(driver)

# Navegar a la URL y resolver el reCAPTCHA
driver.get(url)
t0 = time.time()
recaptchaSolver.solveCaptcha()
print(f"Time to solve the captcha: {time.time() - t0:.2f} seconds")

# Hacer clic en el botón después de resolver el reCAPTCHA
driver.ele("#recaptcha-verify-button").click()

# Bucle para esperar hasta que el navegador Chromium se cierre
print("Esperando a que el navegador Chromium se cierre...")

time.sleep(5)

print("El navegador Chromium ha sido cerrado. Continuando con el flujo del programa.")

# Cerrar el driver para liberar recursos
driver.close()
