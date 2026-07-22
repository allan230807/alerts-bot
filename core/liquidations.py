import requests
import numpy as np

# Configuración del modelo
VELAS_PERIODO = 20
SIMULACIONES_MC = 2000
PASOS_FUTUROS = 12 # Proyectamos 12 velas (1 hora en TF 5m)
PROBABILIDAD_MINIMA_MC = 70.0 # Porcentaje mínimo de éxito en Monte Carlo

def obtener_klines(symbol, interval="5m", limit=30):
    """Obtiene el histórico de velas para calcular medias, volatilidad y volumen."""
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            # Formato: [Open time, Open, High, Low, Close, Volume, ...]
            return res.json()
    except Exception:
        pass
    return None

def filtro_correlacion_btc():
    """Verifica si BTC está en un movimiento direccional violento (ruido sistémico)."""
    klines_btc = obtener_klines("BTCUSDT", limit=5)
    if not klines_btc:
        return False
    
    precio_inicio = float(klines_btc[0][4])
    precio_fin = float(klines_btc[-1][4])
    variacion = abs((precio_fin - precio_inicio) / precio_inicio) * 100
    
    # Si BTC se movió más de 0.8% en los últimos 25 min, bloqueamos altcoins.
    return variacion > 0.8 

def simulacion_monte_carlo(precios_cierre, precio_actual, media_objetivo):
    """
    Ejecuta una simulación estocástica de Monte Carlo (GBM).
    Retorna la probabilidad (%) de que el precio alcance la media.
    """
    retornos = np.diff(precios_cierre) / precios_cierre[:-1]
    mu = np.mean(retornos)
    sigma = np.std(retornos)
    
    dt = 1 # 1 paso = 1 vela
    exitos = 0
    
    # Distancia al objetivo y stop loss implícito (riesgo asimétrico 1:2)
    distancia_media = abs(media_objetivo - precio_actual)
    
    for _ in range(SIMULACIONES_MC):
        precio_simulado = precio_actual
        trayectoria_exitosa = False
        
        for _ in range(PASOS_FUTUROS):
            Z = np.random.normal(0, 1)
            choque = (mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * Z
            precio_simulado *= np.exp(choque)
            
            # Condición de éxito: El precio simulado cruza la media objetivo
            if (precio_actual < media_objetivo and precio_simulado >= media_objetivo) or \
               (precio_actual > media_objetivo and precio_simulado <= media_objetivo):
                trayectoria_exitosa = True
                break
                
            # Condición de fracaso temprano (Stop loss: se aleja el doble de la distancia)
            if abs(precio_simulado - precio_actual) > (distancia_media * 2):
                break
                
        if trayectoria_exitosa:
            exitos += 1
            
    return (exitos / SIMULACIONES_MC) * 100

def analizar_modelo_reversion(top_bruto):
    """
    Aplica filtros de liquidez, agotamiento de volumen y Monte Carlo.
    """
    perfiles_cuantificados = []
    
    # 1. Filtro sistémico: Si BTC está colapsando o explotando, no operamos reversiones de altcoins.
    mercado_correlacionado = filtro_correlacion_btc()

    for activo in top_bruto:
        symbol = activo["symbol"]
        precio_actual = activo["price"]
        
        # Saltamos el análisis de altcoins si BTC está absorbiendo toda la liquidez
        if mercado_correlacionado and symbol != "BTCUSDT":
            continue

        klines = obtener_klines(symbol, limit=VELAS_PERIODO + 5)
        if not klines:
            continue
            
        cierres = np.array([float(k[4]) for k in klines])
        volumenes = np.array([float(k[5]) for k in klines])
        
        # Ventana de análisis
        cierres_recientes = cierres[-VELAS_PERIODO:]
        media = np.mean(cierres_recientes)
        desviacion = np.std(cierres_recientes)
        
        if desviacion == 0:
            continue
            
        z_score = (precio_actual - media) / desviacion
        senal = None
        prob_mc = 0.0
        
        # Evaluamos extremos estadísticos (Umbral |Z| > 2.5 para mayor precisión)
        if abs(z_score) >= 2.5:
            # 2. Filtro de Agotamiento de Volumen (Volume Exhaustion)
            # Validamos que el volumen de la última vela cerrada sea menor a la vela previa de expansión.
            vol_actual = volumenes[-1]
            vol_previo = volumenes[-2]
            agotamiento = vol_actual < (vol_previo * 0.8) # El volumen debe haber caído al menos 20%
            
            # 3. Order Block / Estructura (Simulado con rechazo de mechas)
            mecha_superior = float(klines[-1][2]) - max(float(klines[-1][1]), float(klines[-1][4]))
            mecha_inferior = min(float(klines[-1][1]), float(klines[-1][4])) - float(klines[-1][3])
            cuerpo = abs(float(klines[-1][4]) - float(klines[-1][1]))
            
            rechazo_bajista = mecha_superior > (cuerpo * 1.5)
            rechazo_alcista = mecha_inferior > (cuerpo * 1.5)

            if z_score <= -2.5 and agotamiento and rechazo_alcista:
                # 4. Motor de Probabilidad: Simulación Monte Carlo para Long
                prob_mc = simulacion_monte_carlo(cierres, precio_actual, media)
                if prob_mc >= PROBABILIDAD_MINIMA_MC:
                    senal = f"🟢 LONG SETUP (Reversión Alcista) | Probabilidad MC: {prob_mc:.1f}%"
                    
            elif z_score >= 2.5 and agotamiento and rechazo_bajista:
                # 4. Motor de Probabilidad: Simulación Monte Carlo para Short
                prob_mc = simulacion_monte_carlo(cierres, precio_actual, media)
                if prob_mc >= PROBABILIDAD_MINIMA_MC:
                    senal = f"🔴 SHORT SETUP (Reversión Bajista) | Probabilidad MC: {prob_mc:.1f}%"

        perfiles_cuantificados.append({
            "symbol": symbol,
            "price": precio_actual,
            "change_hour": activo["change_hour"],
            "z_score": z_score,
            "obi": 0, # Mantenido por compatibilidad de estructura, puedes inyectar el Order Book real aquí
            "reversion_signal": senal,
            "mc_probability": prob_mc
        })
        
    return perfiles_cuantificados