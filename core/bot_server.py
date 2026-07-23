import os
import requests
from dotenv import load_dotenv
from liquidations import analizar_modelo_reversion

# Cargar variables de entorno
ruta_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(ruta_env) 

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN:
    raise ValueError("⚠️ TELEGRAM_BOT_TOKEN no está definido en las variables de entorno.")
if not CHAT_ID:
    raise ValueError("⚠️ TELEGRAM_CHAT_ID no está definido en las variables de entorno.")

def obtener_precios_actuales():
    """Obtiene los precios actuales del mercado de futuros de Binance."""
    url = "https://fapi.binance.com/fapi/v1/ticker/price"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return {
                item["symbol"]: float(item["price"]) 
                for item in response.json() 
                if item["symbol"].endswith("USDT") and "_" not in item["symbol"]
            }
    except Exception as e:
        print(f"❌ Error de conexión en la API: {e}")
    return None

def enviar_alerta_telegram(texto):
    """Envía el reporte completo directamente a tu chat de Telegram."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        if res.status_code == 200:
            print("✅ Reporte enviado a Telegram con éxito.")
        else:
            print(f"❌ Error al enviar mensaje a Telegram: {res.text}")
    except Exception as e:
        print(f"❌ Excepción al conectar con Telegram: {e}")

def main():
    print("🚀 Ejecutando ciclo único del Motor Quant (TF: 15m | Ventana: 20 velas)...")
    
    precios_actuales = obtener_precios_actuales()
    if not precios_actuales:
        enviar_alerta_telegram("❌ *Error:* El bot falló al conectar con la API de Binance en este ciclo.")
        return
        
    ranking_bruto = [
        {"symbol": simbolo, "change_hour": 0.0, "price": precio_actual}
        for simbolo, precio_actual in precios_actuales.items()
    ]
    
    if not ranking_bruto:
        print("❌ No se pudieron obtener precios.")
        return

    top_bruto = ranking_bruto[:25]
    
    # Análisis aplicando la ventana de 15m
    perfiles_quant = analizar_modelo_reversion(top_bruto)
    
    # Ordenamos priorizando señales activas y luego magnitud de Z-Score
    perfiles_quant.sort(key=lambda x: (x["reversion_signal"] is not None, abs(x["z_score"]) if x["z_score"] else 0), reverse=True)
    top_10 = perfiles_quant[:10]
    
    mercado_estable = all(p["reversion_signal"] is None for p in top_10)
    
    # Construcción del reporte detallado para Telegram
    texto = "📊 *REPORTE QUANT (TEMPORALIDAD 15M)*\n\n"
    if mercado_estable:
        texto += "💤 *Mercado en equilibrio:* Sin desviaciones extremas (|Z| < 2.5).\n"
        texto += "Mostrando Top 10 con su respectiva probabilidad de reversión (Monte Carlo):\n\n"
    else:
        texto += "⚡ *¡ANOMALÍA DETECTADA!* Oportunidades y métricas del Top 10:\n\n"

    for p in top_10:
        z_str = f"{p['z_score']:+.2f}σ" if p['z_score'] is not None else "N/A"
        obi_str = f"{p['obi']:.2f}" if p['obi'] is not None else "N/A"
        prob_mc = p.get("mc_probability", 0.0)
        
        if p["reversion_signal"]:
            texto += f"🚨 *{p['reversion_signal']}*\n"
        else:
            texto += f"🔹 Activo: `{p['symbol']}`\n"
            
        texto += f"  • Precio: `{p['price']}`\n"
        texto += f"  • Z-Score: `{z_str}` | OBI: `{obi_str}`\n"
        texto += f"  • Prob. Reversión (Monte Carlo): `{prob_mc:.1f}%`\n\n"

    enviar_alerta_telegram(texto)
    print("🏁 Ciclo de análisis finalizado con éxito.")

if __name__ == "__main__":
    main()