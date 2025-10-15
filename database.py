import sqlite3
import os
from datetime import datetime, timedelta
import pytz

# Configuración
DB_FOLDER = 'data'
DB_NAME = 'clima.db'
DB_PATH = os.path.join(DB_FOLDER, DB_NAME)

# Zona horaria de Chile
TIMEZONE = pytz.timezone('America/Santiago')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Permite acceder a columnas por nombre
    return conn


def init_database():
    """
    Inicializa la base de datos creando las tablas necesarias si no existen.
    
    Tablas:
    - sensor_data: Datos capturados por los sensores
    - predictions: Predicciones del modelo ML
    """
    if not os.path.exists(DB_FOLDER):
        os.makedirs(DB_FOLDER)
        print(f"Carpeta '{DB_FOLDER}' creada.")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabla para datos de sensores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            temperatura REAL NOT NULL,
            humedad REAL NOT NULL,
            presion REAL,
            sensor_id TEXT NOT NULL,
            ubicacion TEXT,
            CONSTRAINT check_temperatura CHECK (temperatura BETWEEN -50 AND 60),
            CONSTRAINT check_humedad CHECK (humedad BETWEEN 0 AND 100)
        )
    ''')
    
    # Tabla para predicciones del modelo
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            prediction_time DATETIME NOT NULL,
            temperatura_pred REAL NOT NULL,
            humedad_pred REAL NOT NULL,
            presion_pred REAL,
            confidence REAL,
            model_version TEXT,
            CONSTRAINT check_confidence CHECK (confidence BETWEEN 0 AND 1)
        )
    ''')
    
    # Índices para mejorar consultas por fecha
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_sensor_timestamp 
        ON sensor_data(timestamp)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_prediction_timestamp 
        ON predictions(timestamp)
    ''')
    
    conn.commit()
    conn.close()
    
    print("Base de datos inicializada correctamente.")


# ==================== FUNCIONES PARA DATOS DE SENSORES ====================

def insert_sensor_data(temperatura, humedad, presion=None, sensor_id='arduino_1', ubicacion='Lab'):
    """
    Inserta un nuevo registro de datos de sensor.
    
    Args:
        temperatura (float): Temperatura en grados Celsius
        humedad (float): Humedad relativa en porcentaje
        presion (float, optional): Presión atmosférica en hPa
        sensor_id (str): Identificador del sensor/Arduino
        
    Returns:
        int: ID del registro insertado
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO sensor_data (temperatura, humedad, presion, sensor_id, ubicacion)
        VALUES (?, ?, ?, ?, ?)
    ''', (temperatura, humedad, presion, sensor_id, ubicacion))
    
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return record_id


def get_latest_sensor_data(limit=10):
    """
    Obtiene los últimos N registros de sensores.
    
    Args:
        limit (int): Número de registros a obtener
        
    Returns:
        list: Lista de diccionarios con los datos
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM sensor_data 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    # Convertir a lista de diccionarios
    result = []
    for row in rows:
        result.append({
            'id': row['id'],
            'timestamp': row['timestamp'],
            'temperatura': row['temperatura'],
            'humedad': row['humedad'],
            'presion': row['presion'],
            'sensor_id': row['sensor_id'],
            'ubicacion': row['ubicacion'] if 'ubicacion' in row.keys() else None
        })
    
    return result


def get_sensor_data_by_range(start_date, end_date):
    """
    Obtiene datos de sensores en un rango de fechas.
    
    Args:
        start_date (str): Fecha inicial (formato: 'YYYY-MM-DD HH:MM:SS')
        end_date (str): Fecha final (formato: 'YYYY-MM-DD HH:MM:SS')
        
    Returns:
        list: Lista de diccionarios con los datos
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM sensor_data 
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
    ''', (start_date, end_date))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            'id': row['id'],
            'timestamp': row['timestamp'],
            'temperatura': row['temperatura'],
            'humedad': row['humedad'],
            'presion': row['presion'],
            'sensor_id': row['sensor_id'],
            'ubicacion': row['ubicacion']
        })
    
    return result


def get_sensor_stats():
    """
    Obtiene estadísticas de los datos de sensores.
    
    Returns:
        dict: Diccionario con promedios, máximos y mínimos
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            AVG(temperatura) as temp_promedio,
            MAX(temperatura) as temp_max,
            MIN(temperatura) as temp_min,
            AVG(humedad) as humedad_promedio,
            MAX(humedad) as humedad_max,
            MIN(humedad) as humedad_min,
            AVG(presion) as presion_promedio,
            COUNT(*) as total_registros
        FROM sensor_data
    ''')
    
    row = cursor.fetchone()
    conn.close()
    
    return {
        'temperatura': {
            'promedio': round(row['temp_promedio'], 2) if row['temp_promedio'] else None,
            'max': row['temp_max'],
            'min': row['temp_min']
        },
        'humedad': {
            'promedio': round(row['humedad_promedio'], 2) if row['humedad_promedio'] else None,
            'max': row['humedad_max'],
            'min': row['humedad_min']
        },
        'presion': {
            'promedio': round(row['presion_promedio'], 2) if row['presion_promedio'] else None
        },
        'total_registros': row['total_registros']
    }


# ==================== FUNCIONES PARA PREDICCIONES ====================

def insert_prediction(prediction_time, temperatura_pred, humedad_pred, 
                     presion_pred=None, confidence=None, model_version='v1.0'):
    """
    Inserta una nueva predicción del modelo.
    
    Args:
        prediction_time (str): Hora para la cual se hace la predicción
        temperatura_pred (float): Temperatura predicha
        humedad_pred (float): Humedad predicha
        presion_pred (float, optional): Presión predicha
        confidence (float, optional): Nivel de confianza de la predicción (0-1)
        model_version (str): Versión del modelo ML
        
    Returns:
        int: ID del registro insertado
    """
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


def get_latest_predictions(limit=10):
    """
    Obtiene las últimas N predicciones.
    
    Args:
        limit (int): Número de predicciones a obtener
        
    Returns:
        list: Lista de diccionarios con las predicciones
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM predictions 
        ORDER BY timestamp DESC 
        LIMIT ?
    ''', (limit,))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            'id': row['id'],
            'timestamp': row['timestamp'],
            'prediction_time': row['prediction_time'],
            'temperatura_pred': row['temperatura_pred'],
            'humedad_pred': row['humedad_pred'],
            'presion_pred': row['presion_pred'],
            'confidence': row['confidence'],
            'model_version': row['model_version']
        })
    
    return result


def get_future_predictions():
    """
    Obtiene las predicciones para tiempos futuros.
    
    Returns:
        list: Lista de predicciones futuras
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        SELECT * FROM predictions 
        WHERE prediction_time > ?
        ORDER BY prediction_time ASC
    ''', (now,))
    
    rows = cursor.fetchall()
    conn.close()
    
    result = []
    for row in rows:
        result.append({
            'id': row['id'],
            'timestamp': row['timestamp'],
            'prediction_time': row['prediction_time'],
            'temperatura_pred': row['temperatura_pred'],
            'humedad_pred': row['humedad_pred'],
            'presion_pred': row['presion_pred'],
            'confidence': row['confidence'],
            'model_version': row['model_version']
        })
    
    return result

# ==================== SCRIPT PRINCIPAL ====================

if __name__ == '__main__':
    """
    Script para inicializar la base de datos y hacer pruebas.
    Ejecutar: python database.py
    """
    print("Inicializando base de datos...")
    init_database()
    
    # Insertar datos de prueba
    print("\nInsertando datos de prueba...")
    
    # Datos de sensores
    sensor_id_1 = insert_sensor_data(22.5, 65.3, 1013.2, 'arduino_1')
    sensor_id_2 = insert_sensor_data(21.8, 68.1, 1012.8, 'arduino_2')
    print(f"Insertados {sensor_id_1} y {sensor_id_2} registros de sensores")
    
    # Predicciones
    future_time = datetime.now(TIMEZONE) + timedelta(hours=1)
    pred_id = insert_prediction(
        future_time.strftime('%Y-%m-%d %H:%M:%S'),
        23.1, 63.5, 1013.5, 0.89, 'v1.0'
    )
    print(f"Insertada predicción con ID: {pred_id}")
    
    # Mostrar últimos datos
    print("\nÚltimos datos de sensores:")
    latest = get_latest_sensor_data(5)
    for data in latest:
        print(f"   [{data['timestamp']}] {data['sensor_id']}: {data['temperatura']}°C, {data['humedad']}%")
    
    # Mostrar estadísticas
    print("\nEstadísticas:")
    stats = get_sensor_stats()
    print(f"   Temperatura promedio: {stats['temperatura']['promedio']}°C")
    print(f"   Humedad promedio: {stats['humedad']['promedio']}%")
    print(f"   Total de registros: {stats['total_registros']}")
    
    print("\nBase de datos lista para usar")
