import os
import urllib
import random
import pydub
import speech_recognition
import time
from DrissionPage.common import Keys
from DrissionPage import ChromiumPage


class RecaptchaSolver:
    def __init__(self, driver):
        self.driver = driver

    def solveCaptcha(self):
        print("[INFO] Iniciando solución de CAPTCHA")

        # Localizar el iframe del checkbox reCAPTCHA. Si no existe, no hay un
        # captcha v2 estándar que podamos resolver de forma automática.
        try:
            iframe_inner = self.driver.ele("@title=reCAPTCHA", timeout=3)
        except Exception:
            iframe_inner = None

        if not iframe_inner:
            print("[INFO] No se detectó un reCAPTCHA v2 estándar; resuélvelo manualmente en el navegador.")
            return

        time.sleep(0.1)

        try:
            print("[INFO] Haciendo clic en el checkbox del reCAPTCHA...")
            iframe_inner('.rc-anchor-content', timeout=1).click()
        except Exception:
            print("[ERROR] No se pudo hacer clic en el checkbox del reCAPTCHA; resuélvelo manualmente.")
            return

        try:
            print("[INFO] Esperando a que aparezca el reto del reCAPTCHA...")
            self.driver.wait.ele_displayed("xpath://iframe[contains(@title, 'recaptcha')]", timeout=10)
        except Exception:
            print("[INFO] No apareció un reto adicional (quizá ya quedó resuelto).")

        time.sleep(5)
        if self.isSolved():
            print("[INFO] CAPTCHA resuelto tras el primer clic.")
            return

        try:
            print("[INFO] Localizando el iframe del reto...")
            iframe = self.driver.ele("xpath://iframe[contains(@title, 'recaptcha')]", timeout=3)
        except Exception:
            iframe = None

        if not iframe:
            print("[INFO] No se encontró el iframe del reto; resuélvelo manualmente.")
            return

        try:
            print("[INFO] Haciendo clic en el botón de audio del reCAPTCHA...")
            iframe('#recaptcha-audio-button', timeout=1).click()
        except Exception:
            print("[ERROR] No se pudo acceder al botón de audio; resuélvelo manualmente.")
            return

        time.sleep(0.3)

        try:
            print("[INFO] Obteniendo la fuente del audio...")
            src = iframe('#audio-source').attrs['src']
        except Exception:
            print("[ERROR] No se pudo obtener la fuente del audio; resuélvelo manualmente.")
            return

        try:
            print("[INFO] Descargando el archivo de audio...")
            path_to_mp3 = os.path.normpath(os.path.join(
                (os.getenv("TEMP") if os.name == "nt" else "/tmp/") + str(random.randrange(1, 1000)) + ".mp3"))
            path_to_wav = os.path.normpath(os.path.join(
                (os.getenv("TEMP") if os.name == "nt" else "/tmp/") + str(random.randrange(1, 1000)) + ".wav"))
            urllib.request.urlretrieve(src, path_to_mp3)
        except Exception:
            print("[ERROR] No se pudo descargar el archivo de audio; resuélvelo manualmente.")
            return

        try:
            print("[INFO] Convirtiendo el archivo MP3 a WAV...")
            sound = pydub.AudioSegment.from_mp3(path_to_mp3)
            sound.export(path_to_wav, format="wav")
        except Exception:
            print("[ERROR] No se pudo convertir el audio (¿falta ffmpeg?); resuélvelo manualmente.")
            return

        try:
            print("[INFO] Reconociendo el audio...")
            sample_audio = speech_recognition.AudioFile(path_to_wav)
            r = speech_recognition.Recognizer()
            with sample_audio as source:
                audio = r.record(source)
            key = r.recognize_google(audio)
            print("[INFO] Texto reconocido:", key)
        except Exception:
            print("[ERROR] No se pudo reconocer el audio; resuélvelo manualmente.")
            return

        try:
            print("[INFO] Ingresando el texto reconocido en el reCAPTCHA...")
            iframe('#audio-response').input(key.lower())
            time.sleep(0.1)
            iframe('#audio-response').input(Keys.ENTER)
        except Exception:
            print("[ERROR] No se pudo ingresar el texto; resuélvelo manualmente.")
            return

        time.sleep(0.4)

    def isSolved(self):
        solved = False
        try:
            print("[INFO] Verificando si el CAPTCHA está resuelto...")
            time.sleep(5)
            solved = "style" in self.driver.ele(".recaptcha-checkbox-checkmark", timeout=1).attrs
            print("[INFO] CAPTCHA resuelto:", solved)
        except Exception:
            print("[INFO] No se pudo verificar el estado del CAPTCHA.")
        return solved
