import time
from pathlib import Path
import pandas as pd
import requests
from loguru import logger

def leer_csv_con_reintentos(ruta: Path, reintentos: int = 2) -> pd.DataFrame:
    """Lee un archivo CSV local implementando reintentos básicos."""
    for intento in range(1, reintentos + 1):
        try:
            df = pd.read_csv(ruta)
            return df
        except (FileNotFoundError, pd.errors.ParserError) as e:
            logger.warning(f"⚠️ Intento {intento} falló para {ruta.name}: {e}")
            if intento == reintentos:
                raise e
            time.sleep(0.5)

def cargar_datos_pagos(config: dict, base_path: Path) -> tuple:
    """Carga las 3 fuentes de datos de Olist desde el almacenamiento local."""
    logger.info("📂 Iniciando la extracción de fuentes de datos locales...")
    
    archivos_a_cargar = {
        "pagos": base_path / config["rutas"]["pagos"],
        "ordenes": base_path / config["rutas"]["ordenes"],
        "clientes": base_path / config["rutas"]["clientes"]
    }
    
    dataframes = {}
    for clave, ruta in archivos_a_cargar.items():
        try:
            logger.info(f"   ↳ Cargando {ruta.name}...")
            dataframes[clave] = leer_csv_con_reintentos(ruta)
        except Exception as e:
            logger.error(f"🚨 Error crítico al procesar el archivo '{ruta.name}': {e}")
            continue

    if len(dataframes) < len(archivos_a_cargar):
        raise RuntimeError("🚨 No se pudo completar el pipeline por falta de dependencias de datos.")
        
    logger.success("✅ Todas las fuentes locales se cargaron exitosamente.")
    return dataframes["pagos"], dataframes["ordenes"], dataframes["clientes"]

def obtener_tipo_cambio_dolar(config: dict, reintentos: int = 3) -> float:
    """
    Consume la API de mindicador.cl para obtener el valor del dólar observado.
    Si la API falla tras todos los intentos, aplica un valor de respaldo (Fallback)
    para garantizar la continuidad operativa del negocio.
    """
    url = config["apis"]["mindicador_url"]
    logger.info("🌐 Conectando con la API externa de mindicador.cl...")
    
    for intento in range(1, reintentos + 1):
        try:
            # Timeout de 5 segundos para que no se quede pegado tanto tiempo si está caída
            respuesta = requests.get(url, timeout=5)
            respuesta.raise_for_status()
            
            datos = respuesta.json()
            valor_dolar = float(datos["serie"][0]["valor"])
            logger.success(f"💱 API Exitosa: 1 USD = ${valor_dolar} CLP")
            return valor_dolar
            
        except Exception as e:
            logger.warning(f"⚠️ Intento {intento} falló para la API (Timeout/Red): {e}")
            if intento < reintentos:
                time.sleep(0.5 * intento)
            
    # === MECANISMO DE TOLERANCIA A FALLOS (FALLBACK) ===
    VALOR_RESPALDO = 930.0
    logger.error("🚨 La API de mindicador.cl no responde tras agotar los reintentos.")
    logger.warning(f"🔄 ACTIVANDO PLAN DE CONTINGENCIA: Usando valor de cambio hardcodeado de respaldo: $ {VALOR_RESPALDO} CLP")
    return VALOR_RESPALDO