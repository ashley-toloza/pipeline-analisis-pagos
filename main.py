import sys
from pathlib import Path
import os
import sqlite3
from loguru import logger
import yaml
from dotenv import load_dotenv
import pandas as pd

# --- Configuración de rutas relativas ---
BASE = Path(__file__).resolve().parent
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from src.extract import cargar_datos_pagos, obtener_tipo_cambio_dolar
from src.transform import limpiar_y_validar_datos
from src.pipeline import generar_analisis_pagos, responder_preguntas_negocio

def configurar_logs():
    """Configura el formato profesional de logs en la terminal y en archivo físico."""
    logger.remove()
    
    # 1. Mantener salida bonita por consola (terminal)
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <7}</level> | <cyan>{message}</cyan>",
        level="INFO"
    )
    
    # 2. NUEVO: Escritura física en la raíz para guardar el archivo .log
    ruta_log = BASE / "pipeline.log"
    logger.add(
        ruta_log, 
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <7} | {message}", 
        mode="a", 
        encoding="utf-8"
    )

def cargar_configuracion() -> dict:
    """Lee el archivo yaml y carga de forma segura el entorno .env."""
    # 1. Cargar Variables de Entorno Sensibles (.env)
    ruta_env = BASE / ".env"
    if ruta_env.exists():
        load_dotenv(dotenv_path=ruta_env)
        logger.info("🔐 Archivo .env detectado. Resguardando credenciales y endpoints sensibles...")
        token_oculto = os.getenv("API_AUTH_TOKEN", "")[:8] + "..."
        logger.info(f"   ↳ Token cargado de forma segura: {token_oculto}")
    else:
        logger.warning("⚠️ No se encontró el archivo .env. Se usarán variables locales por defecto.")

    # 2. Cargar Configuración Estructural (YAML)
    ruta_config = BASE / "config.yaml"
    try:
        with open(ruta_config, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.critical(f"🚨 Error crítico de formato en config.yaml: {e}")
        sys.exit(1)
    except FileNotFoundError:
        logger.critical(f"🚨 Archivo config.yaml ausente en la raíz del proyecto.")
        sys.exit(1)

def ejecutar_pipeline():
    """Coordina la ejecución de todo el pipeline automatizado."""
    config = cargar_configuracion()
    ruta_salida = BASE / config["rutas"]["salida_reporte"]
    
    # Control de idempotencia global (Evita reescrituras innecesarias)
    if ruta_salida.exists():
        logger.warning(f"   ↳ El reporte ejecutivo '{ruta_salida.name}' ya existe en almacenamiento.")
        logger.success("✅ El sistema detiene la ejecución de forma segura para no malgastar cómputo.\n")
        return

    # 1. Capa de Extracción (Local + API Externa)
    df_pagos, df_ordenes, df_clientes = cargar_datos_pagos(config, BASE)
    valor_dolar = obtener_tipo_cambio_dolar(config)
    
    # 2. Capa de Transformación (Limpieza y Validación de Contratos)
    df_p_limpio, df_o_limpio = limpiar_y_validar_datos(df_pagos, df_ordenes)
    
    # 3. Capa de Analítica Avanzada y Carga Múltiple (Los 5 Outputs)
    reporte_final, df_completo, pagos_por_metodo, rendimiento_estado_pago = generar_analisis_pagos(
        df_p_limpio, df_o_limpio, df_clientes, valor_dolar, config, BASE
    )
    
    # 4. Despliegue Visual del Reporte de Negocios en Consola
    responder_preguntas_negocio(reporte_final, df_completo, pagos_por_metodo, rendimiento_estado_pago)

    # 5. NUEVO: Consulta SQL Avanzada de Auditoría (No toca los DataFrames del negocio)
    logger.info("🛡️ Iniciando auditoría analítica de consistencia relacional en SQLite...")
    ruta_db = BASE / config["rutas"]["base_datos"]
    
    if ruta_db.exists():
        with sqlite3.connect(ruta_db) as conn:
            query_avanzado = """
                SELECT 
                    payment_type AS [Método de Pago],
                    cantidad_usos AS [Total Transacciones],
                    monto_total_clp AS [Monto Total (CLP)],
                    ROUND((monto_total_clp * 100.0 / (SELECT SUM(monto_total_clp) FROM pagos_por_metodo)), 2) || '%' AS [Participación %]
                FROM pagos_por_metodo
                ORDER BY monto_total_clp DESC;
            """
            df_verificar = pd.read_sql_query(query_avanzado, conn)
            logger.success(f"✅ DB AUDIT PASSED: Archivo '{ruta_db.name}' verificado vía Query Avanzado.")
            
            print("\n" + "-"*75)
            print("🔒 REPORTE DE AUDITORÍA OPERACIONAL (SQL RELACIONAL AVANZADO):")
            print("-"*75)
            
            # Usamos una copia exclusiva para renderizar la consola sin mutar los datos de la DB
            df_visual_audit = df_verificar.copy()
            df_visual_audit[df_visual_audit.columns[2]] = df_visual_audit[df_visual_audit.columns[2]].map(lambda x: f"${x:,.0f}")
            print(df_visual_audit.to_string(index=False))
            print("-"*75 + "\n")
    else:
        logger.error("❌ AUDIT FAILED: El archivo de base de datos relacional no fue encontrado.")

if __name__ == "__main__":
    configurar_logs()
    logger.info("================ PIPELINE OLIST AUTOMATIZADO ================")
    try:
        ejecutar_pipeline()
    except Exception as e:
        logger.critical(f"🚨 El pipeline colapsó debido a un fallo global inesperado: {e}")
        sys.exit(1)
