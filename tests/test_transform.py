import pytest
import pandas as pd
from src.transform import limpiar_y_validar_datos


def test_aislamiento_datos_sucios():
    """
    Prueba unitaria para verificar que la capa de transformación aísla
    correctamente las filas corruptas (valores de pago <= 0 o cuotas < 1).
    """
    # 1. Creamos datos de prueba ficticios (Mock Data)
    df_pagos_mock = pd.DataFrame({
        'order_id': ['orden_1', 'orden_2', 'orden_3'],
        'payment_value': [150.0, -10.0, 200.0],          # El -10.0 es corrupto
        'payment_installments': [3, 1, 0],               # El 0 es corrupto
        'payment_type': ['credit_card', 'boleto', 'voucher']  # Columna requerida por el contrato
    })
    
    df_ordenes_mock = pd.DataFrame({
        'order_id': ['orden_1', 'orden_2', 'orden_3'],
        'customer_id': ['cliente_1', 'cliente_2', 'cliente_3'], # Columna agregada para cumplir el contrato
        'order_status': ['delivered', 'delivered', 'delivered']
    })

    # 2. Ejecutamos la función de transformación
    df_p_limpio, _ = limpiar_y_validar_datos(df_pagos_mock, df_ordenes_mock)

    # 3. Aseveraciones (Asserts)
    # De las 3 filas, solo la 'orden_1' cumple simultáneamente el contrato (valor > 0 y cuotas >= 1)
    assert len(df_p_limpio) == 1, f"Se esperaba 1 fila limpia, pero quedaron {len(df_p_limpio)}"
    assert df_p_limpio.iloc[0]['order_id'] == 'orden_1'


def test_filtrado_ordenes_canceladas():
    """
    Prueba unitaria para verificar que el pipeline excluye del análisis
    las órdenes con estado 'canceled' para no inflar métricas.
    """
    df_pagos_mock = pd.DataFrame({
        'order_id': ['orden_1', 'orden_2', 'orden_3'],
        'payment_value': [100.0, 200.0, 300.0],
        'payment_installments': [1, 2, 1],
        'payment_type': ['credit_card', 'credit_card', 'boleto']
    })
    
    df_ordenes_mock = pd.DataFrame({
        'order_id': ['orden_1', 'orden_2', 'orden_3'],
        'customer_id': ['cliente_1', 'cliente_2', 'cliente_3'], # Columna agregada para cumplir el contrato
        'order_status': ['delivered', 'canceled', 'unavailable'] # Se verifica el comportamiento de filtrado
    })

    _, df_o_limpio = limpiar_y_validar_datos(df_pagos_mock, df_ordenes_mock)

    # El pipeline remueve 'canceled' pero mantiene 'unavailable', por lo que quedan 2 órdenes
    estados_restantes = set(df_o_limpio['order_status'].unique())
    assert len(df_o_limpio) == 2
    assert 'canceled' not in estados_restantes
    assert 'unavailable' in estados_restantes


def test_comportamiento_tipos_y_columnas():
    """
    Prueba unitaria para verificar que los tipos de datos de las columnas clave
    y las estructuras esenciales se mantengan correctas post-transformación.
    """
    df_pagos_mock = pd.DataFrame({
        'order_id': ['orden_1'],
        'payment_value': [50.0],
        'payment_installments': [1],
        'payment_type': ['boleto']
    })
    
    df_ordenes_mock = pd.DataFrame({
        'order_id': ['orden_1'],
        'customer_id': ['cliente_1'], # Columna agregada para cumplir el contrato
        'order_status': ['delivered']
    })

    df_p_limpio, df_o_limpio = limpiar_y_validar_datos(df_pagos_mock, df_ordenes_mock)

    # Validamos tipos de datos requeridos para evitar fallos de agregación en Pandas
    assert pd.api.types.is_numeric_dtype(df_p_limpio['payment_value'])
    assert pd.api.types.is_numeric_dtype(df_p_limpio['payment_installments'])
    
    # Comprobar la integridad de las columnas del contrato de pagos
    columnas_pagos = set(df_p_limpio.columns)
    for col in ['order_id', 'payment_value', 'payment_installments', 'payment_type']:
        assert col in columnas_pagos, f"La columna esencial '{col}' se perdió en la transformación"

    # Comprobar la integridad de las columnas del contrato de órdenes
    columnas_ordenes = set(df_o_limpio.columns)
    for col in ['order_id', 'customer_id', 'order_status']:
        assert col in columnas_ordenes, f"La columna esencial de órdenes '{col}' se perdió"