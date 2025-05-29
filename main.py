from fastapi import FastAPI, requests, HTTPException
from pydantic import BaseModel
from fastapi.responses import JSONResponse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import os
import uuid
import base64
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc

app = FastAPI()
sessions = {}
@app.get("/")
def home():
    return {"mensaje": "API funcionando correctamente"}

class CaptchaInput(BaseModel):
    session_id: str
    captcha: str
    curp: str
    nss: str
    email: str

def iniciar_driver():
    options = Options()
    options.add_argument('--no-sandbox')              # Evita problemas con el sandbox
    options.add_argument('--disable-dev-shm-usage')   # Evita problemas con /dev/shm limitado
    options.add_argument('--headless=new')            # Modo headless moderno, o '--headless' si falla
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-software-rasterizer')
    options.add_argument('--window-size=1920,1080')

    driver = uc.Chrome(options=options)
    return driver

@app.get("/iniciar-sesion")
def iniciar_sesion():

    driver = iniciar_driver()
    driver.get("https://serviciosdigitales.imss.gob.mx/semanascotizadas-web/usuarios/IngresoAsegurado")
    time.sleep(3)
    print("Título de la página:", driver.title)
    print("URL actual:", driver.current_url)
    print("HTML parcial:", driver.page_source[:1000])  # primeros 1000 chars del HTML
    try:
        # Esperar hasta 10 segundos que aparezca el captchaImg
        wait = WebDriverWait(driver, 40)
        imagen_element = wait.until(EC.presence_of_element_located((By.ID, "captchaImg")))

        # Captura la imagen directamente a PNG en memoria
        imagen_png = imagen_element.screenshot_as_png
        # Codifica la imagen a base64
        imagen_base64 = base64.b64encode(imagen_png).decode('utf-8')

        session_id = uuid.uuid4().hex
        sessions[session_id] = {"driver": driver}
        print("Driver en iniciar sesión:", driver)
        return {"session_id": session_id, "captcha_base64": imagen_base64}

    except Exception as e:
        print("Error al obtener captcha:", e)
        driver.save_screenshot("captcha_error.png")  # Para depuración
        raise HTTPException(status_code=500, detail="No se encontró el captcha.")

@app.post("/resolver-captcha")
def resolver_captcha(data: CaptchaInput):
    session_data = sessions.get(data.session_id)
    if not session_data:
        return JSONResponse(status_code=400, content={"error": "Sesión no encontrada"})

    driver = session_data["driver"]
    print("Driver en resolver captcha:", driver)

    try:
        driver.find_element(By.ID, "captcha").send_keys(data.captcha)
        driver.find_element(By.ID, "CURP").send_keys(data.curp)
        driver.find_element(By.ID, "NSS").send_keys(data.nss)
        driver.find_element(By.ID, "Correo").send_keys(data.email)
        driver.find_element(By.ID, "CorreoConfirma").send_keys(data.email)

        time.sleep(1)
        driver.find_element(By.ID, "btnContinuar").click()
        time.sleep(1)
        # Ahora dar click al botón que contiene el atributo name="reporte"
        boton_reporte = driver.find_element(By.NAME, "reporte")
        boton_reporte.click()


        # Puedes hacer más validaciones aquí si deseas

        return {"status": "ok", "detalle": "Formulario enviado"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


