# Pipeline de Analítica y Auditoría — Control de Pagos con Olist

**Proyecto integrador** · DPL1046 · Diplomado en Ingeniería de Datos con Python

## Problema de negocio

Una empresa de e-commerce requiere **centralizar, analizar y auditar el rendimiento financiero de sus métodos de pago** y comportamiento geográfico. Sin este control, se pierde visibilidad sobre las comisiones de pasarelas de pago, estados críticos (órdenes canceladas) y la concentración del flujo de caja en monedas locales (CLP).

## Solución

Pipeline ETL automatizado que procesa datos reales de Olist (e-commerce brasileño, ~100K pedidos):

1. **Extrae** datos de 2 fuentes de forma resiliente: CSVs locales de Olist + API externa de tipo de cambio (`mindicador.cl`) con reintentos y plan de contingencia (*Fallback*).
2. **Transforma**: Aplica contratos de calidad de datos, aísla registros corruptos (valores <= 0) y realiza conversión monetaria dinámica a CLP.
3. **Carga Múltiple**: Genera 4 reportes analíticos CSV independientes y realiza persistencia en una Base de Datos relacional SQLite.
4. **Audita y Analiza**: Ejecuta una interfaz visual en consola con 3 hallazgos clave de negocio y despliega una auditoría relacional mediante un Query SQL Avanzado nativo.

## Cómo correrlo

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Configurar variables de entorno (Opcional)
#    El sistema detecta automáticamente si cuentas con un archivo .env en la raíz

# 3. Correr el pipeline y ver auditoría SQL en consola
python main.py

# 4. Correr la suite de pruebas unitarias
python -m pytest tests/ -v

# 5. Ver reportes analíticos en la carpeta output/ y logs técnicos en pipeline.log

Estructura Real del Proyecto
├── main.py              # Orquestador global (Punto de entrada y auditoría SQL)
├── config.yaml          # Configuración estructural de rutas y endpoints
├── .env                 # Resguardo seguro de credenciales sensibles
├── pipeline.log         # Historial perimetral de logs técnicos (Loguru)
├── requirements.txt     # Dependencias de librerías del proyecto
├── README.md            # Documentación del sistema
├── data/                # CSVs crudos originales de Olist (Ignorados en Git)
│   ├── olist_customers_dataset.csv
│   ├── olist_order_payments_dataset.csv
│   └── olist_orders_dataset.csv
├── output/              # Carpeta de entregables generados por el pipeline
│   ├── olist_analytics.db       # Base de Datos Relacional SQLite (Output 5)
│   ├── ordenes_criticas.csv     # Reporte de órdenes canceladas (Output 4)
│   ├── pagos_por_metodo.csv     # Métricas por tipo de pago (Output 2)
│   ├── rendimiento_por_estado.csv # Matriz cruzada Estado vs Método (Output 3)
│   └── resumen_ejecutivo.csv    # Ventas generales por Estado (Output 1)
├── src/                 # Código fuente modularizado del ETL
│   ├── extract.py       # Extracción local con reintentos + API de tipo de cambio
│   ├── transform.py     # Capa de limpieza y validación de contratos formales
│   └── pipeline.py      # Procesamiento analítico, outputs e insights de negocio
└── tests/               # Suite de pruebas unitarias
    └── test_transform.py # Tests automatizados para las reglas de transformación

🧪 Pruebas Unitarias (Testing)
El proyecto incluye pruebas automatizadas desarrolladas con pytest ubicadas en la carpeta tests/test_transform.py. Estas pruebas se encargan de validar la consistencia de la capa de transformación, asegurando que:

Las funciones de limpieza detecten y aíslen correctamente registros con montos menores o iguales a cero (payment_value <= 0).

Se cumplan estrictamente las restricciones y los contratos formales de datos (data contracts) diseñados para las estructuras de las tablas de Olist antes de permitir su análisis.

Rúbrica y Robustez

Criterio y Cómo se cumple en este proyecto
Funcionalidad (35%),Pipeline modular completo. Integra fuentes de datos híbridas (CSV de Olist + API externa) y genera 5 outputs listos para producción en /output.
Calidad del código (30%),Uso profesional de loguru para trazabilidad física en pipeline.log. Validación estricta por contratos formales de datos empleando asserts verificados mediante pytest.
Buenas prácticas (15%),"Desacoplamiento de rutas mediante config.yaml, uso seguro de entornos .env e Idempotencia Estricta (Validación por Representante: frena de forma segura si los reportes ya existen para cuidar cómputo)."
Mecanismo Fallback,"Tolerancia a fallos: Ante caídas de red o latencia de la API externa, el sistema activa un valor hardcodeado de contingencia ($930.0 CLP) para garantizar la continuidad operativa."
Presentación (20%),Despliegue en consola formateado simétricamente con respuestas directas a preguntas de negocio y reporte SQL Avanzado.