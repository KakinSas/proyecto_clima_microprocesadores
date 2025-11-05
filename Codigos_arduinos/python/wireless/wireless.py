import asyncio
import csv
import os
from datetime import datetime
from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

DEVICE_NAME = "ArduinoEsclavo"
CHARACTERISTIC_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"
EXPECTED_MAC = None  # Se guardará la primera MAC encontrada

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..", "..")
CSV_FILENAME = os.path.join(PROJECT_DIR, "data", "sensor_data.csv")

def parse_sensor_data(line):
    try:
        parts = line.split(",")
        data = {}
        for part in parts:
            key, value = part.split(":")
            data[key.strip()] = float(value.strip())
        return {"temperature": data.get("T", 0), "humidity": data.get("H", 0), "pressure": data.get("P", 0)}
    except Exception as e:
        print(f"Error parseando datos: {e}")
        return None

def save_to_csv(data, source, timestamp):
    try:
        os.makedirs(os.path.dirname(CSV_FILENAME), exist_ok=True)
        file_exists = os.path.isfile(CSV_FILENAME)
        with open(CSV_FILENAME, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "source", "temperature", "humidity", "pressure"])
            writer.writerow([timestamp, source, data["temperature"], data["humidity"], data["pressure"]])
    except Exception as e:
        print(f"Error guardando en CSV: {e}")

def should_accept_sample():
    """Verifica si estamos en un minuto válido para tomar muestras (10, 20, 30, 40, 50, 00)"""
    now = datetime.now()
    minute = now.minute
    return minute % 10 == 0

async def main(db_handler=None):
    global EXPECTED_MAC
    
    print(f"Buscando dispositivo Bluetooth: {DEVICE_NAME}...")
    device = await BleakScanner.find_device_by_name(DEVICE_NAME, timeout=20.0)
    if not device:
        print(f"✗ ERROR: No se encontro el dispositivo {DEVICE_NAME}")
        raise Exception(f"Dispositivo {DEVICE_NAME} no encontrado")
    
    # Verificar MAC si ya se había conectado antes
    if EXPECTED_MAC and device.address != EXPECTED_MAC:
        print(f"⚠️ ADVERTENCIA: MAC cambió de {EXPECTED_MAC} a {device.address}")
    
    if not EXPECTED_MAC:
        EXPECTED_MAC = device.address
        print(f"Dispositivo encontrado: {device.address}")
    
    last_accepted_minute = -1
    connection_lost = False
    
    try:
        async with BleakClient(device, timeout=30.0) as client:
            # Verificar que la conexión está realmente activa
            if not client.is_connected:
                print(f"✗ ERROR: Conexión BLE falló")
                raise Exception("No se pudo establecer conexión BLE")
            
            print(f"✓ Conectado exitosamente a {DEVICE_NAME} ({device.address})")
            print("⏳ Esperando minutos válidos (xx:00, xx:10, xx:20, xx:30, xx:40, xx:50)...")
            
            def notification_handler(sender, data):
                nonlocal last_accepted_minute
                try:
                    line = data.decode("utf-8").strip()
                    if line and line.startswith("T:"):
                        now = datetime.now()
                        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
                        current_minute = now.minute
                        
                        # Verificar si estamos en un minuto válido
                        if should_accept_sample() and current_minute != last_accepted_minute:
                            print(f"📥 WIRELESS [{timestamp}]: {line}")
                            parsed_data = parse_sensor_data(line)
                            if parsed_data:
                                if db_handler:
                                    db_handler.add_sample_to_buffer(source="wireless", temperature=parsed_data["temperature"], humidity=parsed_data["humidity"], pressure=parsed_data["pressure"])
                                save_to_csv(parsed_data, "wireless", timestamp)
                                last_accepted_minute = current_minute
                        # Datos en minutos no válidos se ignoran silenciosamente
                except Exception as e:
                    print(f"✗ ERROR procesando notificacion: {e}")
            
            def disconnected_callback(client):
                nonlocal connection_lost
                connection_lost = True
                print(f"✗ ERROR: Conexión BLE perdida inesperadamente")
            
            client.set_disconnected_callback(disconnected_callback)
            
            await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
            
            # Monitorear conexión activamente
            try:
                while True:
                    if connection_lost or not client.is_connected:
                        print(f"✗ ERROR: Conexión BLE interrumpida")
                        break
                    await asyncio.sleep(5)
            except KeyboardInterrupt:
                pass
            finally:
                try:
                    if client.is_connected:
                        await client.stop_notify(CHARACTERISTIC_UUID)
                except:
                    pass
                    
    except asyncio.TimeoutError:
        print(f"✗ ERROR: Timeout conectando a BLE")
        raise
    except Exception as e:
        print(f"✗ ERROR BLE: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
