from pymongo import MongoClient
from datetime import datetime, timedelta
import threading
import numpy as np

class SensorBuffer:
    """Maneja el buffer de datos del sensor con interpolación lineal y detección de fallos"""
    
    def __init__(self, max_samples=6, source_name="unknown"):
        self.max_samples = max_samples
        self.buffer = []
        self.lock = threading.Lock()
        self.start_time = None
        self.source_name = source_name
        self.expected_interval = timedelta(minutes=10)
        self.current_hour = None  # Hora actual del buffer (ej: 15 para las 15:xx)
        self.last_check_time = datetime.now()
    
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
    
    def interpolate_missing_sample(self):
        """Interpola linealmente si falta 1 muestra (5 en vez de 6)
        IMPORTANTE: Esta función DEBE llamarse desde dentro de un 'with self.lock:' existente
        """
        if len(self.buffer) != 5:
            return False
        
        print(f"[WARN] [{self.source_name.upper()}] Solo 5 muestras detectadas, aplicando interpolación lineal...")
        
        # Ordenar por timestamp
        self.buffer.sort(key=lambda x: x['timestamp'])
        
        # Encontrar el hueco más grande entre timestamps consecutivos
        max_gap_index = 0
        max_gap = timedelta(0)
        
        for i in range(len(self.buffer) - 1):
            gap = self.buffer[i + 1]['timestamp'] - self.buffer[i]['timestamp']
            if gap > max_gap:
                max_gap = gap
                max_gap_index = i
        
        # Interpolar entre las dos muestras con mayor hueco
        sample_before = self.buffer[max_gap_index]
        sample_after = self.buffer[max_gap_index + 1]
        
        interpolated_sample = {
            'temperature': (sample_before['temperature'] + sample_after['temperature']) / 2,
            'humidity': (sample_before['humidity'] + sample_after['humidity']) / 2,
            'pressure': (sample_before['pressure'] + sample_after['pressure']) / 2,
            'timestamp': sample_before['timestamp'] + (sample_after['timestamp'] - sample_before['timestamp']) / 2,
            'interpolated': True
        }
        
        # Insertar la muestra interpolada
        self.buffer.insert(max_gap_index + 1, interpolated_sample)
        
        print(f"[SUCCESS] Muestra interpolada insertada: T={interpolated_sample['temperature']:.2f}°C, "
                  f"H={interpolated_sample['humidity']:.2f}%, P={interpolated_sample['pressure']:.2f}hPa")
        
        return True
    
    def calculate_average(self, force=False):
        """Calcula el promedio de las muestras del buffer"""
        with self.lock:
            if len(self.buffer) == 0:
                print(f"[DEBUG] [{self.source_name.upper()}] Buffer vacío - Retornando None")
                return None
            
            print(f"[DEBUG] [{self.source_name.upper()}] Buffer tiene {len(self.buffer)} muestras antes de procesar")
            
            # Si hay 5 muestras, interpolar primero
            if len(self.buffer) == 5:
                print(f"[DEBUG] [{self.source_name.upper()}] Llamando interpolate_missing_sample()...")
                self.interpolate_missing_sample()
                print(f"[DEBUG] [{self.source_name.upper()}] Después de interpolación: {len(self.buffer)} muestras")
            
            # Si aún no hay 6 muestras (menos de 5)
            if len(self.buffer) < 5:
                if force:
                    # Caso de fallo: marcar como N/A
                    print(f"[WARN] [{self.source_name.upper()}] Solo {len(self.buffer)} muestras - Marcando hora como N/A por fallo")
                    return 'NA'
                else:
                    print(f"[WARN] [{self.source_name.upper()}] Insuficientes muestras ({len(self.buffer)}/{self.max_samples})")
                    return None
            
            print(f"[DEBUG] [{self.source_name.upper()}] Calculando promedios con numpy...")
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
            
            print(f"[INFO] [{self.source_name.upper()}] Promedio calculado: T={result['temperature']}°C, "
                      f"H={result['humidity']}%, P={result['pressure']}hPa (interpolado={result['interpolated']})")
            
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
        print(f"[DEBUG] [{source.upper()}] Iniciando upload_hourly_average (force={force})")
        
        buffer = self.buffers[source]
        
        print(f"[DEBUG] [{source.upper()}] Calculando promedio del buffer...")
        avg_data = buffer.calculate_average(force=force)
        
        if avg_data is None:
            print(f"[WARN] [{source.upper()}] calculate_average retornó None - No hay datos suficientes")
            return
        
        # Si MongoDB no está conectado, solo reportar y limpiar buffer
        if self.client is None:
            print(f"[WARN] [{source.upper()}] MongoDB no disponible - Datos solo guardados en CSV local")
            buffer.clear()
            return
        
        print(f"[DEBUG] [{source.upper()}] Verificando duplicados en MongoDB...")
        
        # Verificar si ya existe un registro para esta hora y fuente
        hour_to_check = buffer.start_time.replace(minute=0, second=0, microsecond=0) if buffer.start_time else datetime.now().replace(minute=0, second=0, microsecond=0)
        print(f"[DEBUG] [{source.upper()}] Buscando duplicados para hora {hour_to_check.strftime('%Y-%m-%d %H:00:00')}")
        
        try:
            # Agregar timeout a la consulta para evitar bloqueos
            print(f"[DEBUG] [{source.upper()}] Ejecutando find_one() en MongoDB...")
            existing = self.collection.find_one(
                {
                    'source': source,
                    'start_time': {
                        '$gte': hour_to_check,
                        '$lt': hour_to_check + timedelta(hours=1)
                    }
                },
                max_time_ms=5000  # Timeout de 5 segundos
            )
            print(f"[DEBUG] [{source.upper()}] find_one() completado. Resultado: {'DUPLICADO' if existing else 'NUEVO'}")
            
            if existing:
                print(f"[SKIP] [{source.upper()}] Registro ya existe para hora {hour_to_check.strftime('%H:00')} - Omitiendo inserción")
                buffer.clear()
                return
        except Exception as e:
            print(f"[WARN] [{source.upper()}] Error verificando duplicados: {e} - Continuando con inserción")
        
        # Caso de fallo: datos insuficientes
        if avg_data == 'NA':
            print(f"[DEBUG] [{source.upper()}] avg_data es 'NA' - Preparando documento de fallo")
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
                'reason': 'Insufficient data - sensor failure or connection lost'
            }
            
            try:
                print(f"[DEBUG] [{source.upper()}] Insertando documento N/A en MongoDB...")
                result = self.collection.insert_one(document)
                print(f"[WARN] [{source.upper()}] Hora marcada como N/A por fallo (ID: {result.inserted_id})")
                print(f"   [WARN] Solo {len(buffer.buffer)} muestras recibidas en la última hora")
                
                # Limpiar buffer después de subir
                buffer.clear()
                
            except Exception as e:
                print(f"[ERROR] [{source.upper()}] Error subiendo N/A a MongoDB: {e}")
            
            return
        
        # Caso normal: datos completos
        print(f"[DEBUG] [{source.upper()}] avg_data es válido - Preparando documento normal")
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
        
        print(f"[DEBUG] [{source.upper()}] Documento preparado: T={document['temperature']}, H={document['humidity']}, P={document['pressure']}, samples={document['samples_count']}, interpolated={document['interpolated']}")
        
        try:
            print(f"[DEBUG] [{source.upper()}] Insertando documento en MongoDB...")
            result = self.collection.insert_one(document)
            print(f"[SUCCESS] [{source.upper()}] Promedio horario subido a MongoDB (ID: {result.inserted_id})")
            print(f"   [INFO] T={avg_data['temperature']}°C, H={avg_data['humidity']}%, P={avg_data['pressure']}hPa")
            
            # Limpiar buffer después de subir
            buffer.clear()
            
        except Exception as e:
            print(f"[ERROR] Error subiendo promedio a MongoDB: {e}")
    
    def close(self):
        """Cierra la conexión con MongoDB"""
        self.running = False  # Detener el thread de monitoreo
        if self.client:
            self.client.close()
            print("[SUCCESS] Conexión a MongoDB cerrada")