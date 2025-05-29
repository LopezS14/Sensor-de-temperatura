import json
from flask import Flask, render_template, jsonify
from flask_mqtt import Mqtt
from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap
import psycopg2
from datetime import datetime
from sklearn.cluster import KMeans
import numpy as np

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MQTT_BROKER_URL'] = 'test.mosquitto.org'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_KEEPALIVE'] = 5
app.config['MQTT_TLS_ENABLED'] = False

mqtt = Mqtt(app)
socketio = SocketIO(app)
bootstrap = Bootstrap(app)

# Conexión con TimescaleDB
conn = psycopg2.connect(
    dbname="sensor_data",
    user="Deyita",
    password="D356106",
    host="localhost",
    port=5432
)
cursor = conn.cursor()

@app.route('/')
def index():
    return render_template('charts.html')

@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    mqtt.subscribe('upiih_h')
    mqtt.subscribe('upiih_m')

latest_temp = None
latest_hum = None

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    global latest_temp, latest_hum
    topic = message.topic
    value = float(message.payload.decode())
    now = datetime.utcnow()

    if topic == "upiih_m":
        latest_temp = value
    elif topic == "upiih_h":
        latest_hum = value

    # Emitimos y guardamos solo cuando tenemos ambos valores
    if latest_temp is not None and latest_hum is not None:
        try:
            cursor.execute("""
                INSERT INTO dht_data (time, temperatura, humidity)
                VALUES (%s, %s, %s)
            """, (now, latest_temp, latest_hum))
            conn.commit()

            print(f"[DB] Guardado: {latest_temp}°C, {latest_hum}%")

            # Emitimos por WebSocket
            data = {
                'timestamp': now.isoformat(),
                'temperatura': latest_temp,
                'humidity': latest_hum
            }

            print("Emitido al frontend:", data)
            socketio.emit('mqtt_message', data=data)

        except Exception as e:
            print("Error al insertar en la base de datos:", e)

        # Reseteamos
        latest_temp = None
        latest_hum = None

@mqtt.on_log()
def handle_logging(client, userdata, level, buf):
    pass  # Puedes usar print(level, buf) si quieres ver logs de MQTT

@socketio.on('subscribe')
def handle_subscribe(json_str=None):
    mqtt.subscribe('upiih_m')
    mqtt.subscribe('upiih_h')

@socketio.on('unsubscribe_all')
def handle_unsubscribe_all():
    mqtt.unsubscribe_all()

@socketio.on('load_history')
def handle_load_history(limit=20):
    try:
        cursor.execute("""
            SELECT time, temperatura, humidity FROM dht_data
            ORDER BY time DESC
            LIMIT %s
        """, (limit,))
        rows = cursor.fetchall()
        rows.reverse()  # Para que estén en orden cronológico

        data = [{
            "timestamp": r[0].isoformat(),
            "temperatura": r[1],
            "humidity": r[2]
        } for r in rows]

        socketio.emit('history_data', data)
    except Exception as e:
        print("Error al consultar historial:", e)
        socketio.emit('history_data', [])

# 🔸 Ruta para clustering
@app.route('/ver_clustering')
def ver_clustering():
    try:
        # Obtener últimos 50 datos
        cursor.execute("""
            SELECT temperatura, humidity FROM dht_data
            ORDER BY time DESC
            LIMIT 10
        """)
        rows = cursor.fetchall()

        if len(rows) < 3:
            return jsonify({"error": "No hay suficientes datos para clustering"}), 400

        datos = np.array(rows)

        # KMeans con 3 clusters
        modelo = KMeans(n_clusters=3, random_state=0)
        etiquetas = modelo.fit_predict(datos)

        resultados = []
        for i in range(len(datos)):
            resultados.append({
                "temperatura": datos[i][0],
                "humedad": datos[i][1],
                "cluster": int(etiquetas[i])
            })

        return jsonify(resultados)
    
    except Exception as e:
        print("Error en clustering:", e)
        return jsonify({"error": "Error interno"}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False, debug=True)
