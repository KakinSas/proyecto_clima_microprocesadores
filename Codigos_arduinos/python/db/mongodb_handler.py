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
        self.hour_timeout = timedelta(hours=1, minutes=5)  # 1 hora + 5 min de tolerancia
    
    def add_sample(self, temperature, humidity, pressure):
        """Agrega una muestra al buffer y retorna si necesita procesar"""
        with self.lock:
            current_time = datetime.now()
            
            if self.start_time is None:
                self.start_time = current_time
            
            sample = {
                'temperature': temperature,
                'humidity': humidity,
                'pressure': pressure,
                'timestamp': current_time
            }
            self.buffer.append(sample)
            print(f"📊 [{self.source_name.upper()}] Buffer: {len(self.buffer)}/{self.max_samples} muestras")
            
            return {
                'count': len(self.buffer),
                'needs_processing': len(self.buffer) >= self.max_samples,
                'time_elapsed': current_time - self.start_time
            }
    
    def check_timeout(self):
        """Verifica si ha pasado demasiado tiempo sin completar el buffer"""
        with self.lock:
            if self.start_time is None or len(self.buffer) == 0:
                return False
            
            elapsed = datetime.now() - self.start_time
            
            # Si pasó más de 1 hora sin completar el buffer
            if elapsed > self.hour_timeout:
                print(f"⚠️ [{self.source_name.upper()}] TIMEOUT: {elapsed.total_seconds()/60:.1f} min sin completar buffer")
                return True
            
            return False
    
    def interpolate_missing_sample(self):
        """Interpola linealmente si falta 1 muestra (5 en vez de 6)"""
        with self.lock:
            if len(self.buffer) != 5:
                return False
            
            print("⚠️ Solo 5 muestras detectadas, aplicando interpolación lineal...")
            
            # Ordenar por timestamp
            self.buffer.sort(key=lambda x: x['timestamp'])
            
            # Calcular el intervalo esperado (10 minutos)
            expected_interval = timedelta(minutes=10)
            
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
            
            print(f"✓ Muestra interpolada insertada: T={interpolated_sample['temperature']:.2f}°C, "
                  f"H={interpolated_sample['humidity']:.2f}%, P={interpolated_sample['pressure']:.2f}hPa")
            
            return True
    
    def calculate_average(self, force=False):
        """Calcula el promedio de las muestras del buffer"""
        with self.lock:
            if len(self.buffer) == 0:
                return None
            
            # Si hay 5 muestras, interpolar primero
            if len(self.buffer) == 5:
                self.interpolate_missing_sample()
            
            # Si aún no hay 6 muestras (menos de 5)
            if len(self.buffer) < 5:
                if force:
                    # Caso de fallo: marcar como N/A
                    print(f"⚠️ [{self.source_name.upper()}] Solo {len(self.buffer)} muestras - Marcando hora como N/A por fallo")
                    return 'NA'
                else:
                    print(f"⚠️ [{self.source_name.upper()}] Insuficientes muestras ({len(self.buffer)}/6)")
                    return None
            
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
            
            print(f"📈 [{self.source_name.upper()}] Promedio calculado: T={result['temperature']}°C, "
                  f"H={result['humidity']}%, P={result['pressure']}hPa")
            
            return result
    
    def clear(self):
        """Limpia el buffer y mantiene la última muestra como primera de la siguiente hora"""
        with self.lock:
            if len(self.buffer) > 0:
                last_sample = self.buffer[-1]
                self.buffer = [last_sample]
                self.start_time = datetime.now()
                print("🔄 Buffer reiniciado, última muestra guardada como primera")
            else:
                self.buffer = []
                self.start_time = None


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
        """Establece conexión con MongoDB"""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            self.client.server_info()
            print("✓ Conexión exitosa a MongoDB")
            return True
        except Exception as e:
            print(f"✗ Error conectando a MongoDB: {e}")
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
            print(f"✗ Fuente desconocida: {source}")
            return
        
        buffer = self.buffers[source]
        info = buffer.add_sample(temperature, humidity, pressure)
        
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
        avg_data = buffer.calculate_average(force=force)
        
        if avg_data is None:
            return
        
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
                'reason': 'Insufficient data - sensor failure or connection lost'
            }
            
            try:
                result = self.collection.insert_one(document)
                print(f"⚠️ [{source.upper()}] Hora marcada como N/A por fallo (ID: {result.inserted_id})")
                print(f"   📉 Solo {len(buffer.buffer)} muestras recibidas en la última hora")
                
                # Limpiar buffer después de subir
                buffer.clear()
                
            except Exception as e:
                print(f"✗ Error subiendo N/A a MongoDB: {e}")
            
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
            print(f"✅ [{source.upper()}] Promedio horario subido a MongoDB (ID: {result.inserted_id})")
            print(f"   📊 T={avg_data['temperature']}°C, H={avg_data['humidity']}%, P={avg_data['pressure']}hPa")
            
            # Limpiar buffer después de subir
            buffer.clear()
            
        except Exception as e:
            print(f"✗ Error subiendo promedio a MongoDB: {e}")
    
    def close(self):
        """Cierra la conexión con MongoDB"""
        self.running = False  # Detener el thread de monitoreo
        if self.client:
            self.client.close()
            print("✓ Conexión a MongoDB cerrada")
