import os
import urllib
import random
import pydub
import speech_recognition
import time
from DrissionPage.common import Keys
from DrissionPage import ChromiumPage

# Función para guardar las cookies en un archivo
def save_cookies_to_file(cookies, file_path):
    with open(file_path, 'w') as file:
        for cookie in cookies:
            # Escribe cada cookie en el formato "nombre=valor; dominio; path"
            file.write(f"{cookie['name']}={cookie['value']}; Domain={cookie['domain']}; Path=/\n")

# Inicializar una sesión de ChromiumPage
driver = ChromiumPage()

# Navegar a Google
driver.get("https://www.google.com")

# Esperar un momento para asegurarse de que la página cargue y se establezcan las cookies
time.sleep(2)

# Obtener las cookies de la sesión
try:
    cookies = driver.driver.get_cookies()  # Intentar obtener cookies del controlador subyacente
except AttributeError:
    cookies = driver.cookies()

# Guardar las cookies en el archivo cookies.txt
save_cookies_to_file(cookies, 'cookies.txt')
print("\n\n [*]New cookies generated!")

# Cerrar el driver para finalizar el programa
driver.close()
