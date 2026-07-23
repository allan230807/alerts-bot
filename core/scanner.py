import time
import datetime
import requests
from liquidations import analizar_modelo_reversion
from notifier import enviar_alerta_telegram

def obtener_precios_actuales():
    url = "https://fapi.binance.vision/fapi/v1/ticker/price"
    try:
        response = requests.get(url, timeout=(3, 5))
        if response.status_code == 200:
            return {
                item["symbol"]: float(item["price"]) 
                for item in response.json() 
                if item["symbol"].endswith("USDT") and "_" not in item["symbol"]
            }
    except Exception as e:
        print(f"Error de conexión en la API: {e}")
    return None

def ejecutar_motor_cuantitativo(umbral_zscore_base=2.2):
    print("🚀 Iniciando Motor Quant 24/7 (Z-Score Estocástico + OBI + Reversión a la Media)...")
    precios_base_hora = {}
    hora_actual_registrada = None

    try:
        while True:
            ahora = datetime.datetime.now()
            
            if ahora.hour != hora_actual_registrada:
                print(f"\n⏳ Inicio de hora ({ahora.strftime('%H:00')}). Reiniciando estados...")
                precios_base_hora.clear()
                hora_actual_registrada = ahora.hour

            # Problema corregido: Sintaxis de strftime corregida en el print
            print(f"\n--- Escaneo Cuantitativo Futuros USDT [{ahora.strftime('%Y-%m-%d %H:%M:%S')}] ---")
            
            try:
                precios_actuales = obtener_precios_actuales()
            except Exception as net_err:
                print(f"⚠️ Error recuperando precios de red: {net_err}")
                precios_actuales = None

            if precios_actuales:
                if not precios_base_hora:
                    precios_base_hora = precios_actuales.copy()
                    print("📌 Precios base de hora fijados.")
                else:
                    ranking_bruto = []
                    for simbolo, precio_actual in precios_actuales.items():
                        if simbolo in precios_base_hora:
                            precio_base = precios_base_hora[simbolo]
                            if precio_base > 0:
                                cambio_hora = ((precio_actual - precio_base) / precio_base) * 100
                                ranking_bruto.append({
                                    "symbol": simbolo,
                                    "change_hour": cambio_hora,
                                    "price": precio_actual
                                })

                    if ranking_bruto:
                        ranking_bruto.sort(key=lambda x: abs(x["change_hour"]), reverse=True)
                        top_bruto = ranking_bruto[:20]
                        
                        perfiles_quant = analizar_modelo_reversion(top_bruto)
                        perfiles_quant.sort(key=lambda x: (x["reversion_signal"] is not None, abs(x["z_score"]) if x["z_score"] else 0), reverse=True)
                        top_10 = perfiles_quant[:10]
                        
                        mercado_estable = all(p["reversion_signal"] is None for p in top_10)
                        
                        print("\n📊 REPORTE DEL MODELO CUANTITATIVO (TOP 10):")
                        if mercado_estable:
                            print(f"💤 MERCADO EN EQUILIBRIO: Sin desviaciones estándar significativas.")
                        else:
                            print(f"⚡ ANOMALÍA DETECTADA: Oportunidades de Reversión a la Media:\n")

                        for p in top_10:
                            z_str = f"{p['z_score']:+.2f}σ" if p['z_score'] is not None else "N/A"
                            obi_str = f"{p['obi']:.2f}" if p['obi'] is not None else "N/A"
                            
                            if p["reversion_signal"]:
                                print(f"  🚨 {p['reversion_signal']}")
                                print(f"    ↳ Activo: {p['symbol']} | Precio: {p['price']} | Z-Score: {z_str} | OBI: {obi_str}\n")
                                
                                prob_mc = p.get("mc_probability", 0.0)
                                mensaje_telegram = (
                                    f"🚨 *ALERTA QUANT DE REVERSIÓN* 🚨\n\n"
                                    f"🔹 *Activo:* `{p['symbol']}`\n"
                                    f"💰 *Precio:* `{p['price']}`\n"
                                    f"📊 *Z-Score:* `{z_str}`\n"
                                    f"🎲 *Probabilidad MC:* `{prob_mc:.1f}%`\n\n"
                                    f"_{p['reversion_signal']}_"
                                )
                                enviar_alerta_telegram(mensaje_telegram)
                            else:
                                print(f"  🔹 {p['symbol']} | Cambio Hora: {p['change_hour']:+.2f}% | Precio: {p['price']} | Z-Score: {z_str} | OBI: {obi_str}")
            else:
                print("⚠️ No se pudieron obtener precios en este ciclo. Reintentando en el próximo intervalo...")

            # Sincronización robusta de ciclos
            ahora_fin_ciclo = datetime.datetime.now()
            minuto_actual = ahora_fin_ciclo.minute
            minuto_base = (minuto_actual // 5) * 5
            proxima_vela = ahora_fin_ciclo.replace(minute=minuto_base, second=0, microsecond=0) + datetime.timedelta(minutes=5)
            segundos_espera = (proxima_vela - ahora_fin_ciclo).total_seconds()
            
            print(f"\n⏳ Esperando {int(segundos_espera)}s al siguiente ciclo...")
            time.sleep(max(1, segundos_espera))

    except KeyboardInterrupt:
        print("\n🛑 Motor cuantitativo detenido.")

if __name__ == "__main__":
    ejecutar_motor_cuantitativo()