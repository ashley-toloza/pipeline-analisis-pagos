import sys
from pathlib import Path
import pandas as pd
from loguru import logger

# --- Aseguramos rutas relativas ---
BASE_TRANSFORM = Path(__file__).resolve().parent.parent

def validar_contrato_pagos(df_p: pd.DataFrame) -> None:
    """
    Lanza un AssertionError claro si los datos de pagos no cumplen las expectativas.
    Implementa las buenas prácticas de contratos de datos vistas en clase.
    """
    logger.info("🔍 Validando contrato de calidad en datos de Pagos...")

    # Regla 1: No deben faltar columnas clave para el negocio
    columnas_clave = {"order_id", "payment_value", "payment_installments", "payment_type"}
    faltan = columnas_clave - set(df_p.columns)
    assert not faltan, f"Faltan columnas obligatorias en pagos: {faltan}"

    # Regla 2: El valor del pago debe ser estrictamente numérico
    assert pd.api.types.is_numeric_dtype(df_p["payment_value"]), \
        "La columna payment_value NO es numérica"

    # Regla 3: No se permiten montos negativos en el reporte limpio
    assert (df_p["payment_value"] >= 0).all(), "Hay montos de pago negativos en el dataset"

    # Regla 4: Las cuotas (installments) deben ser de al menos 1
    assert (df_p["payment_installments"] >= 1).all(), "Hay registros con cuotas menores a 1"

    logger.success("✅ Validación OK: El dataset de pagos cumple el contrato formal.")


def validar_contrato_ordenes(df_o: pd.DataFrame) -> None:
    """
    Lanza un AssertionError si el dataset de órdenes viola el contrato estructural.
    """
    logger.info("🔍 Validando contrato de calidad en datos de Órdenes...")

    # Regla 1: Columnas requeridas para los cruces de tablas
    columnas_clave = {"order_id", "customer_id", "order_status"}
    faltan = columnas_clave - set(df_o.columns)
    assert not faltan, f"Faltan columnas obligatorias en órdenes: {faltan}"

    # Regla 2: No deben existir órdenes duplicadas (order_id debe ser llave primaria única)
    assert not df_o["order_id"].duplicated().any(), "Hay order_id duplicados en el dataset de órdenes"

    logger.success("✅ Validación OK: El dataset de órdenes cumple el contrato formal.")


def limpiar_y_validar_datos(df_payments: pd.DataFrame, df_orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Capa de Transformación: Aísla datos corruptos, aplica filtros de negocio 
    y ejecuta los contratos de datos antes de permitir el paso al análisis.
    """
    logger.info("🧹 Iniciando etapa de Transformación y Validación...")

    # 1. AISLAMIENTO Y LIMPIEZA DE PAGOS (Valores válidos)
    filtro_pagos_validos = (df_payments["payment_value"] > 0) & (df_payments["payment_installments"] >= 1)
    df_payments_limpio = df_payments[filtro_pagos_validos].copy()
    
    filas_invalidas = len(df_payments) - len(df_payments_limpio)
    if filas_invalidas > 0:
        logger.warning(f"   ↳ Se aislaron {filas_invalidas} filas inválidas en pagos (valores <= 0 o vacíos).")

    # 2. EJECUCIÓN DEL CONTRATO DE PAGOS (Asserts del profesor)
    validar_contrato_pagos(df_payments_limpio)

    # 3. FILTRADO ESTRATÉGICO DE ÓRDENES (Excluir canceladas para no inflar métricas)
    df_orders_limpio = df_orders[df_orders["order_status"] != "canceled"].copy()
    logger.info(f"   ↳ Órdenes procesadas: {len(df_orders_limpio)} válidas de un total de {len(df_orders)}.")

    # 4. EJECUCIÓN DEL CONTRATO DE ÓRDENES (Asserts del profesor)
    validar_contrato_ordenes(df_orders_limpio)

    return df_payments_limpio, df_orders_limpio
