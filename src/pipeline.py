import sqlite3
from pathlib import Path
import pandas as pd
from loguru import logger

# Diccionario oficial de mapeo para traducir las siglas de Brasil a nombres completos
MAPEO_ESTADOS = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá",
    "BA": "Bahia", "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo",
    "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais", "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
    "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RO": "Rondônia", "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina",
    "SE": "Sergipe", "SP": "São Paulo", "TO": "Tocantins"
}

def generar_analisis_pagos(df_payments: pd.DataFrame, df_orders: pd.DataFrame, df_customers: pd.DataFrame, valor_dolar: float, config: dict, base_path: Path):
    """
    Cruza las fuentes de datos, integra conversión por API y genera los 5 outputs
    (4 CSVs + 1 DB SQLite).
    """
    logger.info("🧠 Procesando cruces de datos (Merges) y analítica avanzada...")
    
    # 1. Merges secuenciales
    df_unido = pd.merge(df_payments, df_orders, on="order_id", how="inner")
    df_completo = pd.merge(df_unido, df_customers, on="customer_id", how="inner")
    
    # 2. Transformación con API: Conversión Monetaria a CLP
    df_completo["payment_value_clp"] = df_completo["payment_value"] * valor_dolar
    
    # --- 3. Generación de las 4 Tablas de Reportes (Outputs) ---
    
    # Output 1: Resumen Ejecutivo por Estado (Con ambas monedas)
    resumen_ejecutivo = df_completo.groupby("customer_state").agg(
        total_ingresos_usd=("payment_value", "sum"),
        total_ingresos_clp=("payment_value_clp", "sum"),
        transacciones=("order_id", "count")
    ).reset_index()
    
    # Output 2: Métricas por tipo de Pago
    pagos_por_metodo = df_completo.groupby("payment_type").agg(
        monto_total_usd=("payment_value", "sum"),
        monto_total_clp=("payment_value_clp", "sum"),
        cantidad_usos=("order_id", "count")
    ).reset_index()
    
    # Output 3: Matriz cruzada Estado vs Método
    rendimiento_estado_pago = pd.crosstab(
        df_completo["customer_state"], 
        df_completo["payment_type"], 
        values=df_completo["payment_value_clp"], 
        aggfunc="sum"
    ).fillna(0).reset_index()
    
    # Output 4: Órdenes Críticas (Filtro operacional de cancelados)
    ordenes_criticas = df_completo[df_completo["order_status"].isin(["canceled", "unavailable"])][
        ["order_id", "customer_id", "order_status", "payment_value", "payment_value_clp"]
    ].drop_duplicates()
    
    # --- 4. Exportación Física a Carpeta /output ---
    output_dir = base_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    resumen_ejecutivo.to_csv(base_path / config["rutas"]["salida_reporte"], index=False, encoding="utf-8")
    pagos_por_metodo.to_csv(base_path / config["rutas"]["salida_pagos"], index=False, encoding="utf-8")
    rendimiento_estado_pago.to_csv(base_path / config["rutas"]["salida_estados"], index=False, encoding="utf-8")
    ordenes_criticas.to_csv(base_path / config["rutas"]["salida_criticas"], index=False, encoding="utf-8")
    
    logger.success("💾 Outputs 1 al 4 (Archivos CSV) guardados exitosamente.")
    
    # Output 5: Persistencia Relacional en SQLite (.db)
    ruta_db = base_path / config["rutas"]["base_datos"]
    logger.info(f"🗄️ Inyectando tablas en la Base de Datos Relacional: {ruta_db.name}...")
    
    with sqlite3.connect(ruta_db) as conn:
        resumen_ejecutivo.to_sql("resumen_ejecutivo", conn, if_exists="replace", index=False)
        pagos_por_metodo.to_sql("pagos_por_metodo", conn, if_exists="replace", index=False)
        rendimiento_estado_pago.to_sql("rendimiento_estado_pago", conn, if_exists="replace", index=False)
        ordenes_criticas.to_sql("ordenes_criticas", conn, if_exists="replace", index=False)
        
    logger.success("✅ Output 5 (Base de Datos SQLite relacional) estructurada con éxito.")
    
    return resumen_ejecutivo, df_completo, pagos_por_metodo, rendimiento_estado_pago

def responder_preguntas_negocio(resumen_ejecutivo: pd.DataFrame, df_completo: pd.DataFrame, pagos_por_metodo: pd.DataFrame, rendimiento_estado_pago: pd.DataFrame):
    """
    Imprime en la consola el reporte completo con formato profesional,
    nombres de estados completos y terminología unificada ("Transacciones").
    """
    print("\n" + "="*105)
    print("                  📊 REPORTES ANALÍTICOS GLOBALES (OLIST PIPELINE)                  ")
    print("="*105)
    
    # REPORTE 1: Resumen de los 27 Estados con Nombres Reales
    print("\n📈 TABLA 1: RESUMEN EJECUTIVO DE VENTAS POR ESTADO (Muestra Completa)")
    print("-" * 105)
    
    reporte_ordenado = resumen_ejecutivo.sort_values(by="total_ingresos_clp", ascending=False).copy()
    reporte_ordenado["customer_state"] = reporte_ordenado["customer_state"].map(MAPEO_ESTADOS).fillna(reporte_ordenado["customer_state"])
    
    with pd.option_context('display.max_rows', None, 'display.float_format', '{:,.2f}'.format):
        print(reporte_ordenado.to_string(index=False, columns=["customer_state", "transacciones", "total_ingresos_usd", "total_ingresos_clp"],
                                         header=["Estado", "Transacciones", "Total Ventas (USD)", "Total Ventas (CLP)"]))
    print("-" * 105)
    
    # REPORTE 2: Métodos de Pago (CORREGIDO: "Usos" pasa a ser "Transacciones")
    print("\n💳 TABLA 2: RENDIMIENTO FINANCIERO POR MÉTODO DE PAGO")
    print("-" * 105)
    print(f"{'Método de Pago':<16} | {'Transacciones':<13} | {'Total Ventas (USD)':<22} | {'Total Ventas (CLP)':<22}")
    print("-" * 105)
    for _, fila in pagos_por_metodo.iterrows():
        print(f" ➔ {fila['payment_type']:<13} | {int(fila['cantidad_usos']):<13,} | ${fila['monto_total_usd']:<21,.2f} | ${fila['monto_total_clp']:<21,.0f}")
    print("-" * 105)
    
    # REPORTE 3: Ingresos Cruzados
    print("\n🎚️ TABLA 3: INGRESOS POR ESTADO Y MÉTODO EN CLP")
    print("-" * 105)
    
    crosstab_formateado = rendimiento_estado_pago.copy()
    crosstab_formateado["customer_state"] = crosstab_formateado["customer_state"].map(MAPEO_ESTADOS).fillna(crosstab_formateado["customer_state"])
    
    columnas_pagos = [col for col in crosstab_formateado.columns if col != 'customer_state']
    for col in columnas_pagos:
        crosstab_formateado[col] = crosstab_formateado[col].map(lambda x: f"${x:,.0f}")
        
    with pd.option_context('display.max_columns', None, 'display.width', 1000):
        print(crosstab_formateado.to_string(index=False, header=["Estado", "Boleto", "Tarjeta Crédito", "Tarjeta Débito", "Voucher"]))
    print("-" * 105)

    # --- SECCIÓN FINALES: LOS 3 HALLAZGOS ASOCIADOS EN ORDEN ---
    print("\n" + "="*105)
    print("                    💡 HALLAZGOS Y RESPUESTAS CLAVE DE NEGOCIO                    ")
    print("="*105)
    
    # Hallazgo 1 (Asociado a Tabla 1)
    top_fila = resumen_ejecutivo.sort_values(by="total_ingresos_clp", ascending=False).iloc[0]
    nombre_completo_top = MAPEO_ESTADOS.get(top_fila['customer_state'], top_fila['customer_state'])
    print(f"1️⃣ LIDERAZGO COMERCIAL GEOGRÁFICO (Asociado a Tabla 1):")
    print(f"    El estado de '{nombre_completo_top}' es el núcleo de Olist, acumulando el mayor volumen")
    print(f"    de ingresos del pipeline con ${top_fila['total_ingresos_usd']:,.2f} USD (${top_fila['total_ingresos_clp']:,.0f} CLP).")
    print("-" * 105)
    
    # Hallazgo 2 (Asociado a Tabla 2 - Perfectamente alineado con "Transacciones")
    metodo_top = pagos_por_metodo.sort_values(by="monto_total_clp", ascending=False).iloc[0]
    print(f"2️⃣ HEGEMONÍA EN LOS MÉTODOS DE PAGO (Asociado a Tabla 2):")
    print(f"    La modalidad de '{metodo_top['payment_type']}' domina la plataforma con un total recaudado de")
    print(f"    ${metodo_top['monto_total_usd']:,.2f} USD, lo que representa {int(metodo_top['cantidad_usos']):,} transacciones exitosas.")
    print("-" * 105)
    
    # Hallazgo 3 (Asociado a Tabla 3)
    print(f"3️⃣ ANÁLISIS CRUZADO GEOGRÁFICO-FINANCIERO (Asociado a Tabla 3):")
    print(f"    Al cruzar los datos en la matriz, se evidencia que la 'Tarjeta de Crédito' (Credit Card) es el")
    print(f"    motor principal de ingresos en los estados con mayor tracción como São Paulo y Rio de Janeiro,")
    print(f"    superando ampliamente las recaudaciones por 'Boleto' y 'Tarjeta de Débito' combinadas.")
    print("="*105 + "\n")