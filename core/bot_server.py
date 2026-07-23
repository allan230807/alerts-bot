import os
import requests
from dotenv import load_dotenv
from liquidations import analizar_modelo_reversion

# Cargar .env asegurando la ruta raíz del proyecto
ruta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ruta_env = os.path.join(ruta_raiz, '.env')
load_dotenv(ruta_env, override=True) 

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("⚠️ TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no están definidos en el archivo .env")

# Limpieza estricta de espacios y comillas
TOKEN = str(TOKEN).strip().strip("'").strip('"')
CHAT_ID = str(CHAT_ID).strip().strip("'").strip('"')

def obtener_precios_actuales():
    """Intenta consultar precios en varios endpoints de Binance por si falla el DNS."""
    endpoints = [
        "https://fapi.binance.com/fapi/v1/ticker/price",
        "https://fapi.binance.vision/fapi/v1/ticker/price"
    ]
    
    for url in endpoints:
        try:
            response = requests.get(url, timeout=(3, 5))
            if response.status_code == 200:
                return {
                    item["symbol"]: float(item["price"]) 
                    for item in response.json() 
                    if item["symbol"].endswith("USDT") and "_" not in item["symbol"]
                }
        except Exception as e:
            print(f"⚠️ Fallo conexión con {url}: {e}", flush=True)
            continue
            
    print("❌ Error: Todos los endpoints de Binance fallaron por red/DNS.", flush=True)
    return None

def enviar_alerta_telegram(texto):
    """Envía el reporte a Telegram."""
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": texto,
        "parse_mode": "Markdown"
    }
    try:
        res = requests.post(url, json=payload, timeout=(3, 5))
        if res.status_code == 200:
            print("✅ Reporte enviado a Telegram con éxito.", flush=True)
        else:
            print(f"❌ Error al enviar mensaje a Telegram: {res.text}", flush=True)
    except Exception as e:
        print(f"❌ Excepción al conectar con Telegram: {e}", flush=True)

def main():
    print("🚀 Ejecutando ciclo único del Motor Quant (TF: 15m | Ventana: 20 velas)...", flush=True)
    
    precios_actuales = obtener_precios_actuales()
    if not precios_actuales:
        enviar_alerta_telegram("❌ *Error:* El bot falló al conectar con la API de Binance en este ciclo.")
        return
        
    ranking_bruto = [
        {"symbol": simbolo, "change_hour": 0.0, "price": precio_actual}
        for simbolo, precio_actual in precios_actuales.items()
    ]

    top_bruto = ranking_bruto[:25]
    
    perfiles_quant = analizar_modelo_reversion(top_bruto)
    perfiles_quant.sort(key=lambda x: (x["reversion_signal"] is not None, abs(x["z_score"]) if x["z_score"] else 0), reverse=True)
    top_10 = perfiles_quant[:10]
    
    mercado_estable = all(p["reversion_signal"] is None for p in top_10)
    
    texto = "📊 *REPORTE QUANT (TEMPORALIDAD 15M)*\n\n"
    if mercado_estable:
        texto += "💤 *Mercado en equilibrio:* Sin desviaciones extremas (|Z| < 2.5).\n"
        texto += "Mostrando Top 10 con su respectiva probabilidad de reversión (Monte Carlo):\n\n"
    else:
        texto += "⚡ *¡ANOMALÍA DETECTADA!* Oportunidades y métricas del Top 10:\n\n"

    for p in top_10:
        # Extraer valores con respaldo seguro por si vienen como None o faltan claves
        z_val = p.get('z_score')
        obi_val = p.get('obi')
        price_val = p.get('price', 0.0)
        signal_val = p.get('reversion_signal')
        prob_mc = p.get('mc_probability', 0.0)
        symbol_val = p.get('symbol', 'N/A')

        z_str = f"{z_val:+.2f}σ" if z_val is not None else "N/A"
        obi_str = f"{obi_val:.2f}" if obi_val is not None else "N/A"
        
        if signal_val:
            texto += f"🚨 *{signal_val}*\n"
        else:
            texto += f"🔹 Activo: `{symbol_val}`\n"
            
        texto += f"  • Precio: `{price_val}`\n"
        texto += f"  • Z-Score: `{z_str}` | OBI: `{obi_str}`\n"
        texto += f"  • Prob. Reversión (Monte Carlo): `{prob_mc:.1f}%`\n\n"

    enviar_alerta_telegram(texto)
    print("🏁 Ciclo de análisis finalizado con éxito.", flush=True)

if __name__ == "__main__":
    main()