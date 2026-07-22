import os
import telebot
from dotenv import load_dotenv
from users_db import registrar_usuario
from liquidations import analizar_modelo_reversion
import requests
from telebot import types

# Construimos la ruta exacta hacia el archivo .env que está en la carpeta anterior (la raíz)
ruta_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(ruta_env) 

# Cargar el token desde las variables de entorno
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    raise ValueError("⚠️ TELEGRAM_BOT_TOKEN no está definido en las variables de entorno.")

bot = telebot.TeleBot(TOKEN)

def obtener_precios_rapidos():
    """Obtiene precios actuales para una consulta manual en /status."""
    url = "https://fapi.binance.com/fapi/v1/ticker/price"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return {
                item["symbol"]: float(item["price"])
                for item in res.json()
                if item["symbol"].endswith("USDT") and "_" not in item["symbol"]
            }
    except Exception:
        pass
    return None

@bot.message_handler(commands=['start'])
def comando_start(message):
    chat_id = message.chat.id
    es_nuevo = registrar_usuario(chat_id)
    
    mensaje_bienvenida = (
        "🤖 *¡Bienvenido al Bot Quant de Reversión a la Media!*\n\n"
        "Usa los botones de abajo para interactuar sin necesidad de escribir comandos:"
    )
    
    # Creamos el teclado de botones persistentes
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_status = types.KeyboardButton("📊 Estado / Ranking")
    btn_help = types.KeyboardButton("🧠 Explicación del Modelo")
    markup.add(btn_status, btn_help)
    
    bot.reply_to(message, mensaje_bienvenida, parse_mode="Markdown", reply_markup=markup)
    if es_nuevo:
        print(f"👤 Nuevo usuario registrado: {chat_id}")
@bot.message_handler(func=lambda message: True)
def responder_botones(message):
    texto = message.text
    if texto == "📊 Estado / Ranking":
        # Llamamos a la misma lógica del comando ranking
        comando_status(message)
    elif texto == "🧠 Explicación del Modelo":
        comando_help(message)
    else:
        bot.reply_to(message, "Usa los botones del menú inferior para interactuar. 📉📈")
@bot.message_handler(commands=['status', 'ranking'])
def comando_status(message):
    bot.send_chat_action(message.chat.id, 'typing')
    
    precios_actuales = obtener_precios_rapidos()
    if not precios_actuales:
        bot.reply_to(message, "❌ Error al conectar con Binance. Intenta de nuevo en unos segundos.")
        return
        
    # Como estamos bajo demanda, simulamos un ranking base rápido por volatilidad
    ranking_bruto = []
    for simbolo, precio_actual in precios_actuales.items():
        ranking_bruto.append({
            "symbol": simbolo,
            "change_hour": 0.0, # Valor por defecto para consulta rápida
            "price": precio_actual
        })
    
    if not ranking_bruto:
        bot.reply_to(message, "❌ No se pudieron obtener precios en este momento.")
        return

    # Tomamos el Top 20 para someterlos al modelo estadístico de reversión
    top_bruto = ranking_bruto[:20]
    perfiles_quant = analizar_modelo_reversion(top_bruto)
    
    # Ordenamos con la misma lógica del escáner
    perfiles_quant.sort(key=lambda x: (x["reversion_signal"] is not None, abs(x["z_score"]) if x["z_score"] else 0), reverse=True)
    top_10 = perfiles_quant[:10]
    
    mercado_estable = all(p["reversion_signal"] is None for p in top_10)
    
    texto = "📊 *REPORTE DEL MODELO CUANTITATIVO (TOP 10):*\n\n"
    if mercado_estable:
        texto += "💤 *MERCADO EN EQUILIBRIO:* Sin desviaciones estándar significativas (|Z| < 2.2).\n"
        texto += "Mostrando los 10 activos con mayor actividad estocástica actual:\n\n"
    else:
        texto += "⚡ *ANOMALÍA DETECTADA:* Oportunidades de Reversión a la Media:\n\n"

    for p in top_10:
        z_str = f"{p['z_score']:+.2f}σ" if p['z_score'] is not None else "N/A"
        obi_str = f"{p['obi']:.2f}" if p['obi'] is not None else "N/A"
        prob_mc = p.get("mc_probability", 0.0)
        
        if p["reversion_signal"]:
            texto += f"  🚨 *{p['reversion_signal']}*\n"
            texto += f"    ↳ `{p['symbol']}` | Precio: `{p['price']}` | Z: `{z_str}` | OBI: `{obi_str}` | Prob MC: `{prob_mc:.1f}%`\n\n"
        else:
            texto += f"  🔹 `{p['symbol']}` | Precio: `{p['price']}` | Z: `{z_str}` | OBI: `{obi_str}`\n"

    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def comando_help(message):
    texto = (
        "🧠 *¿Cómo funciona el Modelo Quant?*\n\n"
        "1. *Z-Score:* Identifica precios alejados a más de 2.5 desviaciones estándar de su media de 20 periodos.\n"
        "2. *Volume Exhaustion:* Valida que el volumen de la última vela se reduzca, indicando agotamiento institucional.\n"
        "3. *Monte Carlo (2,000 iteraciones):* Simula trayectorias de precios futuras mediante Movimiento Browniano Geométrico. Solo si la probabilidad de éxito supera el 70%, se emite la señal."
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

if __name__ == "__main__":
    print("🤖 Bot de Telegram escuchando comandos (/start, /status, /help)...")
    bot.infinity_polling()