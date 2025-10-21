# --- partes superiores iguales (imports) ---
import sqlite3
import os
from datetime import datetime, timedelta
import pytz
import pandas as pd

DB_FOLDER = 'data'
DB_NAME = 'clima.db'
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)
TIMEZONE = pytz.timezone('America/Santiago')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Crear tabla sensor_data SIN sensor_id ni ubicacion
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            temperatura REAL NOT NULL,
            humedad REAL NOT NULL,
            presion REAL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            prediction_time DATETIME NOT NULL,
            temperatura_pred REAL NOT NULL,
            humedad_pred REAL,
            presion_pred REAL,
            confidence REAL,
            model_version TEXT,
            CONSTRAINT check_confidence CHECK (confidence BETWEEN 0 AND 1)
        )
    ''')

    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sensor_timestamp ON sensor_data(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_prediction_time ON predictions(prediction_time)')
    conn.commit()
    conn.close()

# --- Insert sensor data simplified (sin sensor_id, ubicacion) ---
def insert_sensor_data(temperatura, humedad, presion=None, timestamp=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if timestamp is None:
        timestamp = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO sensor_data (timestamp, temperatura, humedad, presion)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, temperatura, humedad, presion))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id

# --- Nueva función: carga CSV y agrega por minuto ---
def load_csv_and_aggregate_to_db(csv_path=None):
    """
    Lee Codigos_arduinos/data/sensor_data.csv, agrupa por minuto (promedio)
    e inserta/regenera la tabla sensor_data.
    Si csv_path es None, usa la ruta por defecto.
    """
    base_dir = os.path.dirname(__file__)
    default_path = os.path.join(base_dir, "Codigos_arduinos", "data", "sensor_data.csv")
    csv_path = csv_path or default_path

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV no encontrado en {csv_path}")

    df = pd.read_csv(csv_path)

    # Intentar detectar columna timestamp; si no existe asumir existe 'time' o crear desde índice
    if 'timestamp' not in df.columns:
        # intentar columnas comunes
        if 'time' in df.columns:
            df['timestamp'] = df['time']
        else:
            # si no existe, crear timestamps secuenciales a partir de ahora - len rows
            df['timestamp'] = pd.date_range(end=pd.Timestamp.now(), periods=len(df), freq='S')

    # Parsear timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    if df['timestamp'].isnull().any():
        # fallback: si hay strings tipo unix epoch
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')

    # Asegurar columnas temperatura, humedad, presion
    required = ['temperatura', 'humedad']
    for r in required:
        if r not in df.columns:
            raise ValueError(f"Columna requerida no encontrada en CSV: {r}")

    if 'presion' not in df.columns:
        df['presion'] = None

    # Convertir a timezone local si es naive
    df['timestamp'] = df['timestamp'].dt.tz_localize(None)

    # Agrupar por minuto: redondear timestamp a minuto y promediar
    df['timestamp_min'] = df['timestamp'].dt.floor('T')  # 'T' es minuto
    agg = df.groupby('timestamp_min').agg({
        'temperatura': 'mean',
        'humedad': 'mean',
        'presion': 'mean'
    }).reset_index().rename(columns={'timestamp_min':'timestamp'})

    # Insertar o reemplazar datos en la tabla sensor_data
    conn = get_db_connection()
    cursor = conn.cursor()

    # Aquí elegimos vaciar la tabla y reinsertar (simplifica migraciones)
    cursor.execute('DELETE FROM sensor_data')
    conn.commit()

    insert_q = 'INSERT INTO sensor_data (timestamp, temperatura, humedad, presion) VALUES (?, ?, ?, ?)'
    records = [(row['timestamp'].strftime('%Y-%m-%d %H:%M:%S'), 
                float(row['temperatura']) if not pd.isna(row['temperatura']) else None,
                float(row['humedad']) if not pd.isna(row['humedad']) else None,
                float(row['presion']) if not pd.isna(row['presion']) else None) 
               for _, row in agg.iterrows()]

    cursor.executemany(insert_q, records)
    conn.commit()
    conn.close()
    return len(records)

# --- Insert predictions desde CSV generado por predecir_futuro ---
def insert_prediction(prediction_time, temperatura_pred, humedad_pred, presion_pred=None, confidence=None, model_version='v1.0'):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO predictions 
        (prediction_time, temperatura_pred, humedad_pred, presion_pred, confidence, model_version)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (prediction_time, temperatura_pred, humedad_pred, presion_pred, confidence, model_version))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id

def insert_predictions_from_csv(csv_path):
    if not os.path.exists(csv_path):
        raise FileNotFoundError(csv_path)
    df = pd.read_csv(csv_path)
    # Esperamos columnas: timestamp (o prediction_time), temperatura_predicha
    if 'timestamp' in df.columns:
        pred_time_col = 'timestamp'
    elif 'prediction_time' in df.columns:
        pred_time_col = 'prediction_time'
    else:
        raise ValueError("CSV de predicciones no tiene columna 'timestamp' ni 'prediction_time'")

    for _, row in df.iterrows():
        pt = pd.to_datetime(row[pred_time_col]).strftime('%Y-%m-%d %H:%M:%S')
        temp = float(row.get('temperatura_predicha', row.get('temperatura_pred', row.get('temperatura_predicted', None))))
        # Humedad/presion pueden no existir en CSV de ejemplo. Ajustar si tu modelo predice más features.
        humedad = float(row.get('humedad_pred', row.get('humedad_predicha', None))) if 'humedad_pred' in row.index or 'humedad_predicha' in row.index else None
        presion = float(row.get('presion_pred', None)) if 'presion_pred' in row.index else None
        insert_prediction(pt, temp, humedad, presion, confidence=None, model_version='v1.0')

    return True

# --- Obtener los últimos datos del sensor ---
def get_latest_sensor_data(limit=10):
    """
    Devuelve las últimas lecturas desde la tabla sensor_data.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT timestamp, temperatura, humedad, presion
        FROM sensor_data
        ORDER BY timestamp DESC
        LIMIT ?
    ''', (limit,))
    rows = cursor.fetchall()
    conn.close()

    # Convertir a lista de diccionarios
    return [
        {
            "timestamp": row["timestamp"],
            "temperatura": row["temperatura"],
            "humedad": row["humedad"],
            "presion": row["presion"]
        }
        for row in rows
    ]


# --- Obtener las predicciones futuras ---
def get_future_predictions():
    """
    Devuelve todas las predicciones almacenadas en la tabla predictions.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT prediction_time, temperatura_pred, humedad_pred, presion_pred, confidence, model_version
        FROM predictions
        ORDER BY prediction_time ASC
    ''')
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "prediction_time": row["prediction_time"],
            "temperatura_pred": row["temperatura_pred"],
            "humedad_pred": row["humedad_pred"],
            "presion_pred": row["presion_pred"],
            "confidence": row["confidence"],
            "model_version": row["model_version"]
        }
        for row in rows
    ]
