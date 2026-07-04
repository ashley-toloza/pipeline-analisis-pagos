import os
import time
import requests
import pandas as pd
from loguru import logger

def obtener_valor_seguro(config, seccion, clave, defecto):
    """
    Busca de forma ultra segura un valor dentro del objeto config,
    soportando si es un diccionario anidado, plano o si viene vacío.
    """
    if not isinstance(config, dict):
        return defecto
    
    # Intento 1: Buscar en la sección anidada (ej: config["api"]["factor_brl_usd"])
    if seccion in config and isinstance(config[seccion], dict):
        if clave in config[seccion]:
            return config[seccion][clave]
            
    # Intento 2: Buscar en la raíz por si el YAML se cargó plano (ej: config["factor_brl_usd"])
    if clave in config:
        return config[clave]
        
    return defecto

def leer_csv_con_reintentos(ruta_archivo, config):
    """
    Intenta leer un archivo CSV local usando reintentos seguros.
    """
    retries = obtener_valor_seguro(config, "api", "retries", 3)
    delay = obtener_valor_seguro(config, "api", "retry_delay", 2)
    
    for intento in range(retries):
        try:
            df = pd.read_csv(ruta_archivo)
            return df
        except Exception as e:
            logger.warning(f"Intento {intento + 1}/{retries} falló al leer {ruta_archivo}: {e}")
            if intento < retries - 1:
                time.sleep(delay)
            else:
                logger.error(f"No se pudo leer el archivo físico tras {retries} intentos.")
                raise e

def cargar_datos_pagos(config, base_path):
    """
    Carga los 3 datasets de Olist buscando las rutas de forma segura.
    """
    logger.info("Iniciando la extracción de fuentes locales (CSVs de Olist)...")
    
    # Extrae de forma segura el directorio. Si falla o no existe 'paths', usa 'data'
    folder_name = obtener_valor_seguro(config, "paths", "data_dir", "data")
    data_dir = os.path.join(base_path, folder_name)
    
    path_payments = os.path.join(data_dir, "olist_order_payments_dataset.csv")
    path_orders = os.path.join(data_dir, "olist_orders_dataset.csv")
    path_customers = os.path.join(data_dir, "olist_customers_dataset.csv")
    
    df_payments = leer_csv_con_reintentos(path_payments, config)
    df_orders = leer_csv_con_reintentos(path_orders, config)
    df_customers = leer_csv_con_reintentos(path_customers, config)
    
    logger.success("Los 3 datasets de Olist han sido cargados en memoria exitosamente.")
    return df_payments, df_orders, df_customers

def obtener_tipo_cambio_dolar(config):
    """
    Consulta la API de mindicador.cl obteniendo los parámetros del YAML de forma 100% segura.
    """
    logger.info("Iniciando la extracción remota (API mindicador.cl)...")
    
    # Rescate seguro de variables del Config / YAML
    url = obtener_valor_seguro(config, "api", "url", "https://mindicador.cl/api/dolar")
    timeout = obtener_valor_seguro(config, "api", "timeout", 10)
    retries = obtener_valor_seguro(config, "api", "retries", 3)
    delay = obtener_valor_seguro(config, "api", "retry_delay", 2)
    
    # LA VARIABLE CLAVE: La busca en config["api"]["factor_brl_usd"] o config["factor_brl_usd"]
    FACTOR_BRL_USD = obtener_valor_seguro(config, "api", "factor_brl_usd", 0.19)
    
    for intento in range(retries):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            
            valor_usd_clp = r.json()["serie"][0]["valor"]
            brl_a_clp = valor_usd_clp * FACTOR_BRL_USD
            
            logger.success(
                f"API consultada con éxito: 1 USD = ${valor_usd_clp:.2f} CLP. "
                f"Usando factor detectado ({FACTOR_BRL_USD}) -> 1 BRL ≈ ${brl_a_clp:.2f} CLP"
            )
            return brl_a_clp
            
        except Exception as e:
            logger.warning(f"Intento {intento + 1}/{retries} falló al conectar con la API: {e}")
            if intento < retries - 1:
                time.sleep(delay)
                
    fallback_brl = 180.0
    logger.info(f"Aplicando valor Fallback de resiliencia operativa: 1 BRL = ${fallback_brl} CLP")
    return fallback_brl
