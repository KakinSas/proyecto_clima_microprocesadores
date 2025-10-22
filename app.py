from flask import Flask, render_template, jsonify, request
import threading
import os
import time
import logging
import sys
import re
import glob
from datetime import datetime

# Importa las funciones de database y predicción (ver abajo)
import database
import predecir_futuro as predecir  # archivo modificado (ver sección abajo)

app = Flask(__name__)

# Función para remover emojis (solo en Windows)
def remove_emojis(text):
    """Remueve emojis del texto para compatibilidad con Windows console"""
    if sys.platform.startswith('win'):
        # Patrón para detectar emojis
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002702-\U000027B0"
            u"\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub('', text)
    return text

# Formatter personalizado para consola (sin emojis en Windows)
class ConsoleFormatter(logging.Formatter):
    def format(self, record):
        original_msg = record.getMessage()
        record.msg = remove_emojis(str(record.msg))
        result = super().format(record)
        record.msg = original_msg  # Restaurar mensaje original
        return result

# Configuración de logging
# Handler para archivo (con emojis, UTF-8)
file_handler = logging.FileHandler('app.log', encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

# Handler para consola (sin emojis, compatible con Windows)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ConsoleFormatter('%(asctime)s [%(levelname)s] %(message)s'))

# Configurar logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Variables globales para el hilo de sincronización
sync_thread = None
sync_running = False

# Configuración de sincronización (sin variables de entorno)
CSV_PATH = 'Codigos_arduinos/data/sensor_data.csv'
SYNC_INTERVAL = 60  # Sincronizar cada 60 segundos

def sync_csv_to_database():
    """
    Función que se ejecuta en segundo plano y sincroniza el CSV con la DB.
    Verifica cada SYNC_INTERVAL segundos si hay datos nuevos en el CSV.
    """
    global sync_running
    logger.info(f"🔄 Iniciando sincronización automática de {CSV_PATH} cada {SYNC_INTERVAL}s")
    
    while sync_running:
        try:
            if os.path.exists(CSV_PATH):
                logger.info(f"📥 Sincronizando {CSV_PATH} a la base de datos...")
                rows_added = database.load_csv_and_aggregate_to_db(csv_path=CSV_PATH)
                if rows_added > 0:
                    logger.info(f"✅ Sincronización completada: {rows_added} registros nuevos agregados")
                else:
                    logger.debug(f"ℹ️  Sin datos nuevos para sincronizar")
            else:
                logger.warning(f"⚠️  Archivo {CSV_PATH} no encontrado en ruta absoluta: {os.path.abspath(CSV_PATH)}")
        except FileNotFoundError as e:
            logger.error(f"❌ Error: Archivo no encontrado - {e}")
        except ValueError as e:
            logger.error(f"❌ Error de valor en CSV: {e}")
        except Exception as e:
            logger.error(f"❌ Error inesperado en sincronización automática: {type(e).__name__}: {e}", exc_info=True)
        
        # Esperar antes de la próxima sincronización
        time.sleep(SYNC_INTERVAL)

def start_auto_sync():
    """Inicia el hilo de sincronización automática"""
    global sync_thread, sync_running
    
    if sync_running:
        logger.warning("⚠️  La sincronización automática ya está corriendo")
        return
    
    try:
        sync_running = True
        sync_thread = threading.Thread(
            target=sync_csv_to_database,
            daemon=True  # El hilo se cierra cuando se cierra la app
        )
        sync_thread.start()
        logger.info("🚀 Sincronización automática iniciada exitosamente")
    except Exception as e:
        logger.error(f"❌ Error al iniciar sincronización automática: {e}", exc_info=True)
        sync_running = False

def stop_auto_sync():
    """Detiene el hilo de sincronización automática"""
    global sync_running
    sync_running = False
    logger.info("🛑 Sincronización automática detenida")

# Inicializa DB al arrancar
try:
    logger.info("🗄️  Inicializando base de datos...")
    database.init_database()
    logger.info("✅ Base de datos inicializada correctamente")
except Exception as e:
    logger.error(f"❌ Error al inicializar base de datos: {e}", exc_info=True)

# Inicia sincronización automática al arrancar la app
try:
    start_auto_sync()
except Exception as e:
    logger.error(f"❌ Error crítico al iniciar la aplicación: {e}", exc_info=True)

@app.route('/')
def index():
    try:
        logger.debug("📄 Cargando página principal")
        return render_template('index.html')
    except Exception as e:
        logger.error(f"❌ Error al cargar página principal: {e}", exc_info=True)
        return jsonify({"status": "error", "message": "Error al cargar la página"}), 500

# Endpoint para obtener últimos N registros (sensor_data)
@app.route('/api/sensor/latest', methods=['GET'])
def api_latest_sensor():
    try:
        limit = int(request.args.get('limit', 10))
        logger.debug(f"📊 Consultando últimos {limit} registros del sensor")
        data = database.get_latest_sensor_data(limit=limit)
        logger.debug(f"✅ Retornando {len(data)} registros")
        return jsonify(data)
    except ValueError as e:
        logger.error(f"❌ Error de valor en parámetro limit: {e}")
        return jsonify({"status": "error", "message": "Parámetro 'limit' inválido"}), 400
    except Exception as e:
        logger.error(f"❌ Error al obtener datos del sensor: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint para obtener predicciones futuras (todas o limitadas)
@app.route('/api/predictions/future', methods=['GET'])
def api_future_predictions():
    try:
        limit = int(request.args.get('limit', 0))
        logger.debug(f"🔮 Consultando predicciones futuras (limit={limit})")
        preds = database.get_future_predictions()
        if limit and isinstance(limit, int):
            preds = preds[:limit]
        logger.debug(f"✅ Retornando {len(preds)} predicciones")
        return jsonify(preds)
    except ValueError as e:
        logger.error(f"❌ Error de valor en parámetro limit: {e}")
        return jsonify({"status": "error", "message": "Parámetro 'limit' inválido"}), 400
    except Exception as e:
        logger.error(f"❌ Error al obtener predicciones: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint para forzar carga del CSV y agregación por minuto
@app.route('/api/load_csv', methods=['POST'])
def api_load_csv():
    """
    POST /api/load_csv
    Body JSON opcional: {"csv_path": "/ruta/a/sensor_data.csv"}
    """
    try:
        payload = request.get_json(silent=True) or {}
        csv_path = payload.get('csv_path')
        logger.info(f"📥 Carga manual de CSV solicitada: {csv_path or CSV_PATH}")
        rows_added = database.load_csv_and_aggregate_to_db(csv_path=csv_path)
        logger.info(f"✅ CSV cargado exitosamente: {rows_added} registros agregados")
        return jsonify({
            "status": "ok", 
            "message": "CSV cargado y agregado por minuto a la DB",
            "rows_added": rows_added
        }), 200
    except FileNotFoundError as e:
        logger.error(f"❌ Error: Archivo CSV no encontrado - {e}")
        return jsonify({"status": "error", "message": f"Archivo no encontrado: {e}"}), 404
    except ValueError as e:
        logger.error(f"❌ Error de valor en CSV: {e}")
        return jsonify({"status": "error", "message": f"Error en formato de CSV: {e}"}), 400
    except Exception as e:
        logger.error(f"❌ Error al cargar CSV: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint para ejecutar predicción (bloqueante); opcional: lanzarlo en hilo
@app.route('/api/predict', methods=['POST'])
def api_predict():
    """
    POST /api/predict
    Body JSON: {"horas_futuro": 6, "model_path": null}
    """
    try:
        payload = request.get_json(silent=True) or {}
        horas = int(payload.get('horas_futuro', 6))
        logger.info(f"🔮 Predicción solicitada para {horas} horas futuras")

        # Variable compartida para capturar errores
        prediction_result = {"status": "running", "error": None}

        # Ejecutar la predicción en un hilo para no bloquear (puedes cambiar si quieres bloqueante)
        def run_prediction():
            try:
                logger.info(f"🚀 Iniciando proceso de predicción...")
                
                # 1. Limpiar predicciones antiguas de la base de datos
                deleted = database.clear_predictions()
                logger.info(f"🗑️  Predicciones antiguas eliminadas de BD: {deleted} registros")
                
                # 2. Eliminar CSVs antiguos de predicciones
                old_csvs = glob.glob('predicciones_*_horas_por_minuto.csv')
                for old_csv in old_csvs:
                    try:
                        os.remove(old_csv)
                        logger.info(f"🗑️  CSV antiguo eliminado: {old_csv}")
                    except Exception as e:
                        logger.warning(f"⚠️  No se pudo eliminar {old_csv}: {e}")
                
                # 3. Generar nuevas predicciones
                output_csv = predecir.run_prediction(horas_futuro=horas)
                logger.info(f"📊 Predicción completada, guardando en DB desde {output_csv}")
                # leer CSV y guardar en DB
                database.insert_predictions_from_csv(output_csv)
                prediction_result["status"] = "success"
                logger.info(f"✅ Predicciones guardadas exitosamente en la base de datos")
            except FileNotFoundError as e:
                logger.error(f"❌ Error: Archivo de predicción no encontrado - {e}")
                prediction_result["status"] = "error"
                prediction_result["error"] = f"Archivo no encontrado: {e}"
            except Exception as e:
                logger.error(f"❌ Error en proceso de predicción: {type(e).__name__}: {e}", exc_info=True)
                prediction_result["status"] = "error"
                prediction_result["error"] = str(e)

        thread = threading.Thread(target=run_prediction)
        thread.start()

        return jsonify({"status": "running", "message": f"Predicción por {horas} horas iniciada en background."}), 202
    except ValueError as e:
        logger.error(f"❌ Error de valor en parámetros de predicción: {e}")
        return jsonify({"status": "error", "message": "Parámetros inválidos"}), 400
    except Exception as e:
        logger.error(f"❌ Error al iniciar predicción: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint para verificar el estado de la última predicción
@app.route('/api/predict/status', methods=['GET'])
def api_predict_status():
    """
    GET /api/predict/status
    Devuelve si hay predicciones en la base de datos
    """
    try:
        preds = database.get_future_predictions()
        if preds and len(preds) > 0:
            return jsonify({"status": "success", "count": len(preds)}), 200
        else:
            return jsonify({"status": "no_data", "count": 0}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoints para controlar la sincronización automática
@app.route('/api/sync/status', methods=['GET'])
def api_sync_status():
    """
    GET /api/sync/status
    Devuelve el estado de la sincronización automática
    """
    try:
        logger.debug("🔍 Consultando estado de sincronización")
        status = {
            "running": sync_running,
            "csv_path": CSV_PATH,
            "csv_path_absolute": os.path.abspath(CSV_PATH),
            "csv_exists": os.path.exists(CSV_PATH),
            "interval_seconds": SYNC_INTERVAL
        }
        return jsonify(status), 200
    except Exception as e:
        logger.error(f"❌ Error al consultar estado de sincronización: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sync/start', methods=['POST'])
def api_start_sync():
    """
    POST /api/sync/start
    Inicia la sincronización automática (si está detenida)
    """
    try:
        logger.info("▶️  Solicitud de iniciar sincronización automática")
        start_auto_sync()
        return jsonify({"status": "ok", "message": "Sincronización iniciada"}), 200
    except Exception as e:
        logger.error(f"❌ Error al iniciar sincronización: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sync/stop', methods=['POST'])
def api_stop_sync():
    """
    POST /api/sync/stop
    Detiene la sincronización automática
    """
    try:
        logger.info("⏸️  Solicitud de detener sincronización automática")
        stop_auto_sync()
        return jsonify({"status": "ok", "message": "Sincronización detenida"}), 200
    except Exception as e:
        logger.error(f"❌ Error al detener sincronización: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sync/force', methods=['POST'])
def api_force_sync():
    """
    POST /api/sync/force
    Fuerza una sincronización inmediata (sin esperar el intervalo)
    """
    try:
        logger.info(f"⚡ Sincronización forzada solicitada para {CSV_PATH}")
        if os.path.exists(CSV_PATH):
            rows_added = database.load_csv_and_aggregate_to_db(csv_path=CSV_PATH)
            logger.info(f"✅ Sincronización forzada completada: {rows_added} registros agregados")
            return jsonify({
                "status": "ok", 
                "message": f"Sincronización forzada completada", 
                "rows_added": rows_added
            }), 200
        else:
            logger.warning(f"⚠️  CSV no encontrado en: {os.path.abspath(CSV_PATH)}")
            return jsonify({
                "status": "error", 
                "message": f"CSV no encontrado en {CSV_PATH}",
                "absolute_path": os.path.abspath(CSV_PATH)
            }), 404
    except FileNotFoundError as e:
        logger.error(f"❌ Error: Archivo no encontrado - {e}")
        return jsonify({"status": "error", "message": f"Archivo no encontrado: {e}"}), 404
    except Exception as e:
        logger.error(f"❌ Error al forzar sincronización: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

# Endpoint para ver logs recientes
@app.route('/api/logs', methods=['GET'])
def api_logs():
    """
    GET /api/logs?lines=50
    Devuelve las últimas líneas del archivo de log
    """
    try:
        lines = int(request.args.get('lines', 50))
        log_file = 'app.log'
        
        if not os.path.exists(log_file):
            return jsonify({
                "status": "warning",
                "message": "Archivo de log no existe aún",
                "logs": []
            }), 200
        
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return jsonify({
            "status": "ok",
            "total_lines": len(all_lines),
            "returned_lines": len(recent_lines),
            "logs": [line.strip() for line in recent_lines]
        }), 200
    except ValueError as e:
        logger.error(f"❌ Error de valor en parámetro lines: {e}")
        return jsonify({"status": "error", "message": "Parámetro 'lines' inválido"}), 400
    except Exception as e:
        logger.error(f"❌ Error al leer logs: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    try:
        logger.info("="*60)
        logger.info("🚀 Iniciando aplicación Flask - Sistema de Clima")
        logger.info(f"📁 Directorio de trabajo: {os.getcwd()}")
        logger.info(f"📄 CSV Path: {os.path.abspath(CSV_PATH)}")
        logger.info(f"⏱️  Intervalo de sincronización: {SYNC_INTERVAL} segundos")
        logger.info("="*60)
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("⚠️  Aplicación interrumpida por el usuario (Ctrl+C)")
        stop_auto_sync()
    except Exception as e:
        logger.critical(f"❌ Error crítico al iniciar la aplicación: {e}", exc_info=True)
    finally:
        logger.info("👋 Aplicación finalizada")