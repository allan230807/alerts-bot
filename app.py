import os
import sys
import pytz
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

# 1. Ajuste para el intérprete de Python: 
# Permite que los archivos dentro de 'core' se encuentren entre sí (ej. bot_server a liquidations)
ruta_core = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'core')
if ruta_core not in sys.path:
    sys.path.insert(0, ruta_core)

# 2. Ajuste para VS Code (Pylance): 
# Usamos el prefijo 'core.' para que el linter visual lo detecte correctamente
from core.bot_server import main as ejecutar_analisis_quant

app = Flask(__name__)

def tarea_programada():
    print("⏳ Ejecutando análisis cuantitativo (Top 10)...", flush=True)
    try:
        ejecutar_analisis_quant()
    except Exception as e:
        print(f"❌ Error al ejecutar el modelo: {e}", flush=True)

# Configuramos el Scheduler (se ejecuta cada 1 hora)
scheduler = BackgroundScheduler(timezone=pytz.utc)
scheduler.add_job(func=tarea_programada, trigger="interval", hours=1)
scheduler.start()

# Ruta Web requerida por Render para mantener el servicio activo
@app.route('/')
def home():
    return "✅ Render Web Service activo. El Bot Quant escanea el mercado cada 1 hora."

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
