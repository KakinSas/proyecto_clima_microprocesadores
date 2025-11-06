import asyncio
import threading
import sys
import os
import time
import importlib.util
import signal

def import_module_from_path(module_name, file_path):
 """
 Importa un módulo desde una ruta específica
 """
 spec = importlib.util.spec_from_file_location(module_name, file_path)
 module = importlib.util.module_from_spec(spec)
 sys.modules[module_name] = module
 spec.loader.exec_module(module)
 return module

# Rutas a los módulos
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
wired_path = os.path.join(SCRIPT_DIR, 'wired', 'wired.py')
wireless_path = os.path.join(SCRIPT_DIR, 'wireless', 'wireless.py')
db_path = os.path.join(SCRIPT_DIR, 'db', 'mongodb_handler.py')

# Importar módulos
wired = import_module_from_path('wired', wired_path)
wireless = import_module_from_path('wireless', wireless_path)
mongodb_handler = import_module_from_path('mongodb_handler', db_path)

# MongoDB URI
MONGODB_URI = "mongodb+srv://benjotenks:msfaObufcIQ6IP6d@cluster0.d18af.mongodb.net/microprocesadores"

# Variables de control
wired_running = True
wireless_running = True
db_handler = None

def init_database():
    """Inicializa la conexión a MongoDB"""
    global db_handler
    try:
        db_handler = mongodb_handler.MongoDBHandler(MONGODB_URI)
        return db_handler
    except Exception as e:
        print(f"ERROR: Error inicializando MongoDB: {e}")
        return None

def run_wired():
    """
    Ejecuta el lector serial en un thread separado con reintentos automáticos
    """
    retry_count = 0
    while wired_running:
        try:
            if retry_count > 0:
                print(f"WIRED: Reintentando conexión (intento #{retry_count})...")
            else:
                print("Iniciando módulo WIRED (Serial)...")
            
            wired.main(db_handler=db_handler)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            retry_count += 1
            print(f"ERROR: Error en módulo WIRED: {e}")
            print(f"WIRED: Esperando 5 segundos antes de reintentar...")
            time.sleep(5)

async def run_wireless():
    """
    Ejecuta el lector Bluetooth de forma asíncrona con reintentos automáticos
    """
    retry_count = 0
    while wireless_running:
        try:
            if retry_count > 0:
                print(f"WIRELESS: Reintentando conexión (intento #{retry_count})...")
            else:
                print("Iniciando módulo WIRELESS (Bluetooth)...")
            
            await wireless.main(db_handler=db_handler)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            retry_count += 1
            print(f"ERROR: Error en módulo WIRELESS: {e}")
            print(f"WIRELESS: Esperando 5 segundos antes de reintentar...")
            await asyncio.sleep(5)

async def main():
    """
    Función principal que ejecuta ambos módulos en paralelo
    """
    global db_handler, wired_running, wireless_running
    
    print("="*70)
    print("Sistema de Adquisición de Datos - Buffer Horario + MongoDB")
    print("="*70)
    print("Configuración del sistema:")
    print("  WIRED: Puerto Serial /dev/ttyACM0")
    print("  WIRELESS: Bluetooth (ArduinoEsclavo)")
    print("  CSV Local: data/sensor_data.csv")
    print("  MongoDB: Promedios horarios (12 muestras/hora)")
    print("  Muestreo: Cada 5 minutos (xx:00, xx:05, xx:10, ..., xx:55)")
    print("  Interpolación: Con historial completo del CSV")
    print("  Mínimo requerido: 70% de datos (9 de 12 muestras)")
    print("  Auto-reintento: Activado")
    print("="*70)
    print()
    
    # Inicializar MongoDB
    db_handler = init_database()
    
    if db_handler is None:
        print("WARNING: Continuando sin MongoDB (solo guardado local)")
    
    # Crear thread para el módulo wired (serial)
    wired_thread = threading.Thread(target=run_wired, daemon=True)
    wired_thread.start()
    
    # Pequeña pausa para que wired inicie primero
    await asyncio.sleep(2)
    
    # Ejecutar el módulo wireless (bluetooth) en el loop asyncio principal
    try:
        await run_wireless()
    except KeyboardInterrupt:
        print("\nPrograma terminado por el usuario")
        wired_running = False
        wireless_running = False
        if db_handler:
            db_handler.close()

def _ignore_sighup_if_possible():
    """Ignora SIGHUP para que el proceso continúe si se cierra la terminal (Linux/Raspberry Pi)."""
    try:
        if hasattr(signal, "SIGHUP"):
            signal.signal(signal.SIGHUP, signal.SIG_IGN)
            print("Ignorando SIGHUP: el proceso continuará si se cierra la terminal.")
    except Exception:
        # En algunos entornos puede no ser aplicable; continuar sin fallar
        pass


def run_supervisado():
    """Ejecuta main() en bucle con auto-reinicio ante fallos inesperados.

    - Ctrl+C (KeyboardInterrupt) detiene definitivamente.
    - Si la terminal se cierra, se ignora SIGHUP (en Linux) y el proceso sigue.
    - Ante cualquier otra excepción, se reinicia con backoff.
    """
    global db_handler, wired_running, wireless_running
    _ignore_sighup_if_possible()
    reintentos = 0
    backoff_max = 30
    while True:
        try:
            asyncio.run(main())
            # Si main() retornó normalmente, reiniciar tras breve pausa
            print("main() finalizó; reiniciando en 5s...")
            reintentos = 0
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nPrograma terminado por el usuario")
            wired_running = False
            wireless_running = False
            if db_handler:
                db_handler.close()
            break
        except Exception as e:
            reintentos = min(reintentos + 1, 6)
            espera = min(5 * reintentos, backoff_max)
            print(f"ERROR: Error toplevel: {e}")
            print(f"Reiniciando en {espera}s...")
            time.sleep(espera)


if __name__ == "__main__":
    run_supervisado()

