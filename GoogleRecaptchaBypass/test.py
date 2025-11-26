from DrissionPage import ChromiumPage 
from RecaptchaSolver import RecaptchaSolver
import time

 
driver = ChromiumPage()
recaptchaSolver = RecaptchaSolver(driver)

time.sleep(2)
driver.get("https://www.google.com/recaptcha/api2/demo")

time.sleep(2)
t0 = time.time()
recaptchaSolver.solveCaptcha()
print(f"Time to solve the captcha: {time.time()-t0:.2f} seconds")

driver.ele("#recaptcha-demo-submit").click()

driver.close()
