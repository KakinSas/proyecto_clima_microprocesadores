from pymongo import MongoClient
from datetime import datetime, timedelta
import threading
import numpy as np
import csv
import os
import time

class SensorBuffer:
    """Maneja el buffer de datos del sensor con interpolación con historial y detección de fallos"""
    
    def __init__(self, max_samples=12, source_name="unknown"):
        self.max_samples = max_samples
        self.buffer = []
        self.lock = threading.Lock()
        self.start_time = None
        self.source_name = source_name
        self.expected_interval = timedelta(minutes=5)
        self.current_hour = None  # Hora actual del buffer (ej: 15 para las 15:xx)
        self.last_check_time = datetime.now()
        self.history = []  # Historial completo para interpolación avanzada
    
    def add_sample(self, temperature, humidity, pressure):
        """Agrega una muestra al buffer y retorna si necesita procesar"""
        with self.lock:
            current_time = datetime.now()
            
            # Si es una nueva hora del reloj, forzar procesamiento del buffer anterior
            if self.current_hour is not None and current_time.hour != self.current_hour:
                print(f"[INFO] [{self.source_name.upper()}] Nueva hora detectada ({self.current_hour}:xx -> {current_time.hour}:xx)")
                if len(self.buffer) > 0:
                    # Marcar que necesita procesamiento inmediato
                    return {
                        'count': len(self.buffer),
                        'needs_processing': True,
                        'force_process': True,
                        'reason': 'hour_change',
                        'time_elapsed': current_time - self.start_time if self.start_time else timedelta(0)
                    }
            
            # Inicializar hora actual si es la primera muestra
            if self.current_hour is None:
                self.current_hour = current_time.hour
                self.start_time = current_time
                print(f"[INFO] [{self.source_name.upper()}] Iniciando buffer para hora {self.current_hour}:00")
            
            sample = {
                'temperature': temperature,
                'humidity': humidity,
                'pressure': pressure,
                'timestamp': current_time
            }
            self.buffer.append(sample)
            print(f"[INFO] [{self.source_name.upper()}] Buffer: {len(self.buffer)}/{self.max_samples} muestras (hora {self.current_hour}:xx)")
            
            return {
                'count': len(self.buffer),
                'needs_processing': len(self.buffer) >= self.max_samples,
                'force_process': False,
                'time_elapsed': current_time - self.start_time
            }
    
    def check_timeout(self):
        """Verifica si cambió la hora del reloj y el buffer no se procesó"""
        with self.lock:
            current_time = datetime.now()
            
            if self.current_hour is None or len(self.buffer) == 0:
                return False
            
            # Si cambió la hora del reloj y hay datos sin procesar
            if current_time.hour != self.current_hour:
                print(f"[TIMEOUT] [{self.source_name.upper()}] TIMEOUT: Cambio de hora detectado ({self.current_hour}:xx -> {current_time.hour}:xx)")
                print(f"   [WARN] Buffer incompleto con {len(self.buffer)} muestras")
                return True
            
            return False
    
    def load_history_from_csv(self, csv_path):
        """Carga el historial completo del sensor desde el CSV"""
        history = []
        try:
            if not os.path.exists(csv_path):
                return history
            
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['source'] == self.source_name:
                        history.append({
                            'temperature': float(row['temperature']),
                            'humidity': float(row['humidity']),
                            'pressure': float(row['pressure']),
                            'timestamp': datetime.strptime(row['timestamp'], '%Y-%m-%d %H:%M:%S')
                        })
        except Exception as e:
            print(f"[WARN] [{self.source_name.upper()}] Error cargando historial CSV: {e}")
        
        return history
    
    def interpolate_missing_samples(self, csv_path):
        """Interpola muestras faltantes usando regresión lineal con TODO el historial
        IMPORTANTE: Esta función DEBE llamarse desde dentro de un 'with self.lock:' existente
        """
        if len(self.buffer) >= self.max_samples:
            return True  # Buffer completo, no necesita interpolación
        
        missing_count = self.max_samples - len(self.buffer)
        print(f"[WARN] [{self.source_name.upper()}] Faltan {missing_count} muestras, aplicando interpolación con historial completo...")
        
        # Cargar historial desde CSV
        history = self.load_history_from_csv(csv_path)
        
        # Combinar historial con buffer actual
        all_data = history + self.buffer
        
        if len(all_data) < 2:
            print(f"[ERROR] [{self.source_name.upper()}] Sin historial suficiente para interpolar")
            return False
        
        print(f"[INFO] [{self.source_name.upper()}] Usando {len(all_data)} muestras históricas para interpolación")
        
        # Ordenar por timestamp
        all_data.sort(key=lambda x: x['timestamp'])
        self.buffer.sort(key=lambda x: x['timestamp'])
        
        # Encontrar timestamps faltantes en el buffer actual
        if len(self.buffer) == 0:
            return False
        
        expected_times = []
        start_hour = self.buffer[0]['timestamp'].replace(minute=0, second=0, microsecond=0)
        for i in range(12):
            expected_times.append(start_hour + timedelta(minutes=i*5))
        
        existing_times = {s['timestamp'].replace(second=0, microsecond=0) for s in self.buffer}
        missing_times = [t for t in expected_times if t not in existing_times]
        
        # Preparar datos para regresión lineal
        timestamps_numeric = np.array([(d['timestamp'] - all_data[0]['timestamp']).total_seconds() for d in all_data])
        temps = np.array([d['temperature'] for d in all_data])
        humids = np.array([d['humidity'] for d in all_data])
        pressures = np.array([d['pressure'] for d in all_data])
        
        # Calcular regresión lineal para cada métrica
        temp_coef = np.polyfit(timestamps_numeric, temps, 1)
        humid_coef = np.polyfit(timestamps_numeric, humids, 1)
        pressure_coef = np.polyfit(timestamps_numeric, pressures, 1)
        
        # Interpolar valores faltantes
        interpolated_count = 0
        for missing_time in missing_times[:missing_count]:
            time_numeric = (missing_time - all_data[0]['timestamp']).total_seconds()
            
            interp_temp = temp_coef[0] * time_numeric + temp_coef[1]
            interp_humid = humid_coef[0] * time_numeric + humid_coef[1]
            interp_pressure = pressure_coef[0] * time_numeric + pressure_coef[1]
            
            # Validar rangos realistas
            interp_temp = max(0, min(50, interp_temp))
            interp_humid = max(0, min(100, interp_humid))
            interp_pressure = max(900, min(1100, interp_pressure))
            
            interpolated_sample = {
                'temperature': round(interp_temp, 2),
                'humidity': round(interp_humid, 2),
                'pressure': round(interp_pressure, 2),
                'timestamp': missing_time,
                'interpolated': True
            }
            
            self.buffer.append(interpolated_sample)
            interpolated_count += 1
            
            print(f"[INFO] [{self.source_name.upper()}] Interpolado {missing_time.strftime('%H:%M')}: T={interp_temp:.2f}°C, H={interp_humid:.2f}%, P={interp_pressure:.2f}hPa")
        
        # Re-ordenar buffer
        self.buffer.sort(key=lambda x: x['timestamp'])
        
        print(f"[SUCCESS] [{self.source_name.upper()}] {interpolated_count} muestras interpoladas exitosamente")
        return True
    
    def calculate_average(self, force=False, csv_path=None):
        """Calcula el promedio de las muestras del buffer aplicando regla del 70%"""
        with self.lock:
            if len(self.buffer) == 0:
                return None
            
            # Regla del 70%: Calcular mínimo requerido (redondeado hacia arriba)
            min_samples_required = int(np.ceil(self.max_samples * 0.7))
            current_percentage = (len(self.buffer) / self.max_samples) * 100
            
            print(f"[INFO] [{self.source_name.upper()}] Buffer: {len(self.buffer)}/{self.max_samples} muestras ({current_percentage:.1f}%)")
            
            # Si no cumple el 70% mínimo
            if len(self.buffer) < min_samples_required:
                if force:
                    print(f"[ERROR] [{self.source_name.upper()}] Solo {current_percentage:.1f}% de datos - Se requiere mínimo 70%")
                    print(f"[ERROR] Hora perdida - Marcando como N/A")
                    return 'NA'
                else:
                    return None
            
            # Si cumple el 70% pero falta alguna muestra, interpolar
            if len(self.buffer) < self.max_samples:
                if csv_path:
                    self.interpolate_missing_samples(csv_path)
                else:
                    print(f"[WARN] [{self.source_name.upper()}] Sin ruta CSV, no se puede interpolar con historial")
            
            # Calcular promedios
            avg_temp = np.mean([s['temperature'] for s in self.buffer])
            avg_humidity = np.mean([s['humidity'] for s in self.buffer])
            avg_pressure = np.mean([s['pressure'] for s in self.buffer])
            
            result = {
                'temperature': round(avg_temp, 2),
                'humidity': round(avg_humidity, 2),
                'pressure': round(avg_pressure, 2),
                'samples_count': len(self.buffer),
                'start_time': self.start_time,
                'end_time': datetime.now(),
                'interpolated': any(s.get('interpolated', False) for s in self.buffer)
            }
            
            print(f"[SUCCESS] [{self.source_name.upper()}] Promedio: T={result['temperature']}°C, H={result['humidity']}%, P={result['pressure']}hPa (interpolado={result['interpolated']})")
            
            return result
    
    def clear(self):
        """Limpia el buffer para la siguiente hora"""
        with self.lock:
            current_time = datetime.now()
            
            # Limpiar buffer completamente
            self.buffer = []
            self.start_time = current_time
            self.current_hour = current_time.hour
            
            print(f"[INFO] [{self.source_name.upper()}] Buffer limpiado, iniciando nueva hora {self.current_hour}:xx")


class MongoDBHandler:
    def __init__(self, uri, database_name="microprocesadores", collection_name="sensores"):
        """Inicializa la conexión a MongoDB"""
        self.uri = uri
        self.database_name = database_name
        self.collection_name = collection_name
        self.client = None
        self.db = None
        self.collection = None
        self.lock = threading.Lock()
        
        # Ruta al CSV de datos históricos
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.join(script_dir, '..', '..')
        self.csv_path = os.path.join(project_dir, 'data', 'sensor_data.csv')
        
        # Buffers para cada fuente de datos
        self.buffers = {
            'wired': SensorBuffer(source_name='wired'),
            'wireless': SensorBuffer(source_name='wireless')
        }
        
        # Thread para monitorear timeouts
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_timeouts, daemon=True)
        self.monitor_thread.start()
        
        self.connect()
    
    def connect(self):
        """Establece conexión con MongoDB con reintentos"""
        max_retries = 3
        retry_delay = 2  # segundos
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    print(f"[INFO] Reintentando conexión a MongoDB (intento {attempt + 1}/{max_retries})...")
                
                # Timeout más largo para Raspberry Pi (30 segundos)
                self.client = MongoClient(
                    self.uri, 
                    serverSelectionTimeoutMS=30000,
                    connectTimeoutMS=30000,
                    socketTimeoutMS=30000
                )
                self.db = self.client[self.database_name]
                self.collection = self.db[self.collection_name]
                
                # Verificar conexión
                self.client.server_info()
                print("[SUCCESS] Conexión exitosa a MongoDB")
                return True
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"[ERROR] Error en intento {attempt + 1}: {e}")
                    import time
                    time.sleep(retry_delay)
                else:
                    print(f"[FATAL] Error conectando a MongoDB después de {max_retries} intentos: {e}")
                    print("[WARN] El sistema continuará funcionando sin MongoDB (solo guardado local en CSV)")
                    return False
        
        return False
    
    def _monitor_timeouts(self):
        """Monitorea los buffers y procesa si hay timeout (más de 1 hora sin completar)"""
        import time
        while self.running:
            time.sleep(60)  # Revisar cada minuto
            
            for source, buffer in self.buffers.items():
                if buffer.check_timeout():
                    # Forzar procesamiento con los datos disponibles o marcar como N/A
                    self.upload_hourly_average(source, force=True)
    
    def add_sample_to_buffer(self, source, temperature, humidity, pressure):
        """
        Agrega una muestra al buffer correspondiente
        
        Args:
            source: 'wired' o 'wireless'
            temperature: Temperatura en °C
            humidity: Humedad en %
            pressure: Presión en hPa
        """
        if source not in self.buffers:
            print(f"[ERROR] Fuente desconocida: {source}")
            return
        
        buffer = self.buffers[source]
        info = buffer.add_sample(temperature, humidity, pressure)
        
        # Si cambió la hora, procesar buffer anterior primero
        if info.get('force_process') and info.get('reason') == 'hour_change':
            print(f"[INFO] [{source.upper()}] Procesando buffer de hora anterior antes de agregar nuevo dato")
            try:
                self.upload_hourly_average(source, force=True)
            except Exception as e:
                print(f"[ERROR] ERROR procesando buffer de hora anterior: {e}")
                # Limpiar buffer forzosamente para evitar quedarse atascado
                buffer.clear()
            
            # Ahora agregar el dato nuevo al buffer limpio
            print(f"[INFO] [{source.upper()}] Agregando muestra nueva a buffer de hora {datetime.now().hour}:xx")
            buffer.add_sample(temperature, humidity, pressure)
            return
        
        # Si el buffer está lleno (6 muestras), calcular promedio y subir
        if info['needs_processing']:
            self.upload_hourly_average(source)
    
    def upload_hourly_average(self, source, force=False):
        """
        Calcula el promedio del buffer y lo sube a MongoDB
        
        Args:
            source: 'wired' o 'wireless'
            force: Si es True, fuerza el procesamiento aunque no esté completo
        """
        buffer = self.buffers[source]
        
        avg_data = buffer.calculate_average(force=force, csv_path=self.csv_path)
        
        if avg_data is None:
            return
        
        # Si MongoDB no está conectado, solo reportar y limpiar buffer
        if self.client is None:
            print(f"[WARN] [{source.upper()}] MongoDB no disponible - Datos guardados en CSV local")
            buffer.clear()
            return
        
        # Verificar si ya existe un registro para esta hora y fuente
        hour_to_check = buffer.start_time.replace(minute=0, second=0, microsecond=0) if buffer.start_time else datetime.now().replace(minute=0, second=0, microsecond=0)
        
        try:
            existing = self.collection.find_one(
                {
                    'source': source,
                    'start_time': {
                        '$gte': hour_to_check,
                        '$lt': hour_to_check + timedelta(hours=1)
                    }
                },
                max_time_ms=5000
            )
            
            if existing:
                print(f"[SKIP] [{source.upper()}] Registro ya existe para hora {hour_to_check.strftime('%H:00')}")
                buffer.clear()
                return
        except Exception as e:
            print(f"[WARN] [{source.upper()}] Error verificando duplicados: {e}")
        
        # Caso de fallo: datos insuficientes
        if avg_data == 'NA':
            document = {
                'source': source,
                'type': 'hourly_average',
                'temperature': None,
                'humidity': None,
                'pressure': None,
                'samples_count': len(buffer.buffer),
                'interpolated': False,
                'start_time': buffer.start_time,
                'end_time': datetime.now(),
                'timestamp': datetime.now(),
                'status': 'FAILURE',
                'reason': 'Insufficient data (less than 70%)'
            }
            
            try:
                result = self.collection.insert_one(document)
                print(f"[FAILURE] [{source.upper()}] Hora {hour_to_check.strftime('%H:00')} marcada como N/A (ID: {result.inserted_id})")
                buffer.clear()
            except Exception as e:
                print(f"[ERROR] [{source.upper()}] Error subiendo N/A: {e}")
            
            return
        
        # Caso normal: datos completos
        document = {
            'source': source,
            'type': 'hourly_average',
            'temperature': avg_data['temperature'],
            'humidity': avg_data['humidity'],
            'pressure': avg_data['pressure'],
            'samples_count': avg_data['samples_count'],
            'interpolated': avg_data['interpolated'],
            'start_time': avg_data['start_time'],
            'end_time': avg_data['end_time'],
            'timestamp': datetime.now(),
            'status': 'OK'
        }
        
        try:
            result = self.collection.insert_one(document)
            print(f"[MONGODB] [{source.upper()}] Subido exitosamente (ID: {result.inserted_id})")
            buffer.clear()
            
        except Exception as e:
            print(f"[ERROR] Error subiendo promedio a MongoDB: {e}")
    
    def close(self):
        """Cierra la conexión con MongoDB"""
        self.running = False  # Detener el thread de monitoreo
        if self.client:
            self.client.close()
            print("[SUCCESS] Conexión a MongoDB cerrada")