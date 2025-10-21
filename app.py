from flask import Flask, render_template, jsonify, request
import threading
import os

# Importa las funciones de database y predicción (ver abajo)
import database
import predecir_futuro as predecir  # archivo modificado (ver sección abajo)

app = Flask(__name__)

# Inicializa DB al arrancar
database.init_database()

@app.route('/')
def index():
    return render_template('index.html')

# Endpoint para obtener últimos N registros (sensor_data)
@app.route('/api/sensor/latest', methods=['GET'])
def api_latest_sensor():
    limit = int(request.args.get('limit', 10))
    data = database.get_latest_sensor_data(limit=limit)
    return jsonify(data)

# Endpoint para obtener predicciones futuras (todas o limitadas)
@app.route('/api/predictions/future', methods=['GET'])
def api_future_predictions():
    limit = int(request.args.get('limit', 0))
    preds = database.get_future_predictions()
    if limit and isinstance(limit, int):
        preds = preds[:limit]
    return jsonify(preds)

# Endpoint para forzar carga del CSV y agregación por minuto
@app.route('/api/load_csv', methods=['POST'])
def api_load_csv():
    """
    POST /api/load_csv
    Body JSON opcional: {"csv_path": "/ruta/a/sensor_data.csv"}
    """
    payload = request.get_json(silent=True) or {}
    csv_path = payload.get('csv_path')
    try:
        database.load_csv_and_aggregate_to_db(csv_path=csv_path)
        return jsonify({"status":"ok", "message":"CSV cargado y agregado por minuto a la DB"}), 200
    except Exception as e:
        return jsonify({"status":"error", "message": str(e)}), 500

# Endpoint para ejecutar predicción (bloqueante); opcional: lanzarlo en hilo
@app.route('/api/predict', methods=['POST'])
def api_predict():
    """
    POST /api/predict
    Body JSON: {"horas_futuro": 6, "model_path": null}
    """
    payload = request.get_json(silent=True) or {}
    horas = int(payload.get('horas_futuro', 6))

    # Variable compartida para capturar errores
    prediction_result = {"status": "running", "error": None}

    # Ejecutar la predicción en un hilo para no bloquear (puedes cambiar si quieres bloqueante)
    def run_prediction():
        try:
            output_csv = predecir.run_prediction(horas_futuro=horas)
            # leer CSV y guardar en DB
            database.insert_predictions_from_csv(output_csv)
            prediction_result["status"] = "success"
        except Exception as e:
            app.logger.error(f"Error en predicción: {e}")
            prediction_result["status"] = "error"
            prediction_result["error"] = str(e)

    thread = threading.Thread(target=run_prediction)
    thread.start()

    return jsonify({"status":"running", "message": f"Predicción por {horas} horas iniciada en background."}), 202

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)