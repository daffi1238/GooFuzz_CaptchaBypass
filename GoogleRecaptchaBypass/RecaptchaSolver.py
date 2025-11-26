import os,urllib,random,pydub,speech_recognition,time
from DrissionPage.common import Keys
from DrissionPage import ChromiumPage 

class RecaptchaSolver:
    def __init__(self, driver):
        self.driver = driver

    def solveCaptcha(self):
        print("[INFO] Iniciando solución de CAPTCHA")
        try:
            print("[INFO] Localizando iframe interno de reCAPTCHA...")
            iframe_inner = self.driver("@title=reCAPTCHA")
            print("[INFO] Iframe encontrado:", iframe_inner)
        except Exception as e:
            print("[ERROR] No se pudo localizar el iframe interno:", e)
            return

        time.sleep(0.1)
        
        try:
            print("[INFO] Haciendo clic en el contenido del reCAPTCHA...")
            iframe_inner('.rc-anchor-content', timeout=1).click()
        except Exception as e:
            print("[ERROR] No se pudo hacer clic en el reCAPTCHA:", e)
            return
        
        try:
            print("[INFO] Esperando que el iframe del reCAPTCHA sea visible...")
            self.driver.wait.ele_displayed("xpath://iframe[contains(@title, 'recaptcha')]", timeout=10)
        except Exception as e:
            print("[ERROR] El iframe no se hizo visible a tiempo:", e)
            return

        time.sleep(5)
        if self.isSolved():
            print("[INFO] CAPTCHA resuelto tras el primer clic.")
            return
        
        try:
            print("[INFO] Localizando nuevo iframe del reCAPTCHA...")
            iframe = self.driver("xpath://iframe[contains(@title, 'recaptcha')]")
            print("[INFO] Iframe encontrado:", iframe)
        except Exception as e:
            print("[ERROR] No se pudo localizar el nuevo iframe:", e)
            return

        try:
            print("[INFO] Haciendo clic en el botón de audio del reCAPTCHA...")
            iframe('#recaptcha-audio-button', timeout=1).click()
        except Exception as e:
            print("[ERROR] No se pudo hacer clic en el botón de audio:", e)
            return

        time.sleep(0.3)

        try:
            print("[INFO] Obteniendo la fuente del audio...")
            src = iframe('#audio-source').attrs['src']
            print("[INFO] Fuente de audio obtenida:", src)
        except Exception as e:
            print("[ERROR] No se pudo obtener la fuente del audio:", e)
            return

        try:
            print("[INFO] Descargando el archivo de audio...")
            path_to_mp3 = os.path.normpath(os.path.join(
                (os.getenv("TEMP") if os.name == "nt" else "/tmp/") + str(random.randrange(1, 1000)) + ".mp3"))
            path_to_wav = os.path.normpath(os.path.join(
                (os.getenv("TEMP") if os.name == "nt" else "/tmp/") + str(random.randrange(1, 1000)) + ".wav"))
            urllib.request.urlretrieve(src, path_to_mp3)
            print("[INFO] Archivo de audio descargado en:", path_to_mp3)
        except Exception as e:
            print("[ERROR] No se pudo descargar el archivo de audio:", e)
            return

        try:
            print("[INFO] Convirtiendo el archivo MP3 a WAV...")
            sound = pydub.AudioSegment.from_mp3(path_to_mp3)
            sound.export(path_to_wav, format="wav")
            print("[INFO] Archivo convertido a WAV:", path_to_wav)
        except Exception as e:
            print("[ERROR] No se pudo convertir el archivo de audio:", e)
            return

        try:
            print("[INFO] Reconociendo el audio...")
            sample_audio = speech_recognition.AudioFile(path_to_wav)
            r = speech_recognition.Recognizer()
            with sample_audio as source:
                audio = r.record(source)
            key = r.recognize_google(audio)
            print("[INFO] Texto reconocido:", key)
        except Exception as e:
            print("[ERROR] No se pudo reconocer el audio:", e)
            return

        try:
            print("[INFO] Ingresando el texto reconocido en el reCAPTCHA...")
            iframe('#audio-response').input(key.lower())
            time.sleep(0.1)
            iframe('#audio-response').input(Keys.ENTER)
        except Exception as e:
            print("[ERROR] No se pudo ingresar el texto en el reCAPTCHA:", e)
            return

        time.sleep(0.4)

        #if self.isSolved():
        #    print("[INFO] CAPTCHA resuelto con éxito.")
        #    return
        #else:
        #    print("[ERROR] Falló la solución del CAPTCHA.")
        #    return

    def isSolved(self):
        try:
            print("[INFO] Verificando si el CAPTCHA está resuelto...")
            time.sleep(5)
            solved = "style" in self.driver.ele(".recaptcha-checkbox-checkmark", timeout=1).attrs
            print("[INFO] CAPTCHA resuelto:", solved)
            return solved
        except Exception as e:
            print("[ERROR] Error al verificar si el CAPTCHA está resuelto:", e)
            return solved