import requests
import numpy as np

# Configuración del modelo (Ventana de 20 velas en temporalidad de 15m = 5 horas)
VELAS_PERIODO = 20
INTERVALO_VELAS = "15m"
SIMULACIONES_MC = 2000
PASOS_FUTUROS = 12 # Proyectamos 12 velas (3 horas en TF 15m)
PROBABILIDAD_MINIMA_MC = 70.0 # Porcentaje mínimo de éxito en Monte Carlo

def obtener_klines(symbol, interval=INTERVALO_VELAS, limit=30):
    """Obtiene el histórico de velas en temporalidad de 15m usando el endpoint libre de restricciones en la nube."""
    url = f"https://dapi.binance.vision/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()
        # Fallback alternativo al endpoint general de visión si el dapi falla
        url_alt = f"https://data-api.binance.vision/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res_alt = requests.get(url_alt, timeout=10)
        if res_alt.status_code == 200:
            return res_alt.json()
    except Exception:
        pass
    return None

def obtener_obi(symbol, limit=20):
    """Consulta el Order Book de Binance y calcula el OBI real usando endpoints seguros para la nube."""
    url = f"https://fapi.binance.vision/fapi/v1/depth?symbol={symbol}&limit={limit}"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            bids_vol = sum([float(item[1]) for item in data.get("bids", [])])
            asks_vol = sum([float(item[1]) for item in data.get("asks", [])])
            
            total_vol = bids_vol + asks_vol
            if total_vol == 0:
                return 0.0
            
            obi = (bids_vol - asks_vol) / total_vol
            return round(obi, 4)
    except Exception:
        pass
    return 0.0

def filtro_correlacion_btc():
    """Verifica si BTC está en un movimiento direccional violento en TF 15m."""
    klines_btc = obtener_klines("BTCUSDT", interval=INTERVALO_VELAS, limit=5)
    if not klines_btc:
        return False
    
    precio_inicio = float(klines_btc[0][4])
    precio_fin = float(klines_btc[-1][4])
    variacion = abs((precio_fin - precio_inicio) / precio_inicio) * 100
    
    return variacion > 1.2 # Umbral ajustado para 15m

def simulacion_monte_carlo(precios_cierre, precio_actual, media_objetivo):
    """Ejecuta simulación estocástica de Monte Carlo (GBM)."""
    retornos = np.diff(precios_cierre) / precios_cierre[:-1]
    mu = np.mean(retornos)
    sigma = np.std(retornos)
    
    dt = 1 
    exitos = 0
    distancia_media = abs(media_objetivo - precio_actual)
    
    for _ in range(SIMULACIONES_MC):
        precio_simulado = precio_actual
        trayectoria_exitosa = False
        
        for _ in range(PASOS_FUTUROS):
            Z = np.random.normal(0, 1)
            choque = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
            precio_simulado *= np.exp(choque)
            
            if (precio_actual < media_objetivo and precio_simulado >= media_objetivo) or \
               (precio_actual > media_objetivo and precio_simulado <= media_objetivo):
                trayectoria_exitosa = True
                break
                
            if abs(precio_simulado - precio_actual) > (distancia_media * 2):
                break
                
        if trayectoria_exitosa:
            exitos += 1
            
    return (exitos / SIMULACIONES_MC) * 100

def analizar_modelo_reversion(top_bruto):
    """Aplica filtros estadísticos basados en velas de 15m y calcula Monte Carlo para todos."""
    perfiles_cuantificados = []
    mercado_correlacionado = filtro_correlacion_btc()

    for activo in top_bruto:
        symbol = activo["symbol"]
        precio_actual = activo["price"]
        
        if mercado_correlacionado and symbol != "BTCUSDT":
            continue

        klines = obtener_klines(symbol, interval=INTERVALO_VELAS, limit=VELAS_PERIODO + 5)
        if not klines:
            continue
            
        cierres = np.array([float(k[4]) for k in klines])
        volumenes = np.array([float(k[5]) for k in klines])
        
        obi_val = obtener_obi(symbol)
        
        cierres_recientes = cierres[-VELAS_PERIODO:]
        media = np.mean(cierres_recientes)
        desviacion = np.std(cierres_recientes)
        
        if desviacion == 0:
            continue
            
        z_score = (precio_actual - media) / desviacion
        senal = None
        
        # Calculamos la probabilidad de Monte Carlo para TODOS los activos del top
        prob_mc = simulacion_monte_carlo(cierres, precio_actual, media)
        
        if abs(z_score) >= 2.5:
            vol_actual = volumenes[-1]
            vol_previo = volumenes[-2]
            agotamiento = vol_actual < (vol_previo * 0.8)
            
            mecha_superior = float(klines[-1][2]) - max(float(klines[-1][1]), float(klines[-1][4]))
            mecha_inferior = min(float(klines[-1][1]), float(klines[-1][4])) - float(klines[-1][3])
            cuerpo = abs(float(klines[-1][4]) - float(klines[-1][1]))
            
            rechazo_bajista = mecha_superior > (cuerpo * 1.5)
            rechazo_alcista = mecha_inferior > (cuerpo * 1.5)

            if z_score <= -2.5 and agotamiento and rechazo_alcista and obi_val > -0.3:
                if prob_mc >= PROBABILIDAD_MINIMA_MC:
                    senal = f"🟢 LONG SETUP (Reversión Alcista)"
                    
            elif z_score >= 2.5 and agotamiento and rechazo_bajista and obi_val < 0.3:
                if prob_mc >= PROBABILIDAD_MINIMA_MC:
                    senal = f"🔴 SHORT SETUP (Reversión Bajista)"

        perfiles_cuantificados.append({
            "symbol": symbol,
            "price": precio_actual,
            "change_hour": activo["change_hour"],
            "z_score": z_score,
            "obi": obi_val,
            "reversion_signal": senal,
            "mc_probability": prob_mc
        })
        
    return perfiles_cuantificados