import math
import requests

def obtener_datos_cuantitativos_libro(simbolo, limite=100):
    url = f"https://fapi.binance.com/fapi/v1/depth?symbol={simbolo}&limit={limite}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            
            if not bids or not asks:
                return None, None

            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
            mid_price = (best_bid + best_ask) / 2.0

            bid_weighted_sum = 0.0
            total_bid_vol = 0.0
            for precio_str, cantidad_str in bids:
                p = float(precio_str)
                q = float(cantidad_str)
                distancia = abs(mid_price - p) / mid_price
                peso = 1.0 / (1.0 + distancia * 100)
                bid_weighted_sum += q * peso
                total_bid_vol += q

            ask_weighted_sum = 0.0
            total_ask_vol = 0.0
            for precio_str, cantidad_str in asks:
                p = float(precio_str)
                q = float(cantidad_str)
                distancia = abs(p - mid_price) / mid_price
                peso = 1.0 / (1.0 + distancia * 100)
                ask_weighted_sum += q * peso
                total_ask_vol += q

            denominador = bid_weighted_sum + ask_weighted_sum
            obi = (bid_weighted_sum - ask_weighted_sum) / denominador if denominador > 0 else 0.0

            return obi, {"bids": total_bid_vol, "asks": total_ask_vol}
    except Exception:
        pass
    return None, None

def calcular_zscore_y_volatilidad(simbolo):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={simbolo}&interval=5m&limit=25"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            velas = response.json()
            if len(velas) < 20:
                return None, None, None

            closes = [float(v[4]) for v in velas]
            highs = [float(v[2]) for v in velas]
            lows = [float(v[3]) for v in velas]

            sma = sum(closes[-20:]) / 20.0
            varianza = sum((c - sma) ** 2 for c in closes[-20:]) / 20.0
            std_dev = math.sqrt(varianza) if varianza > 0 else 0.00000001

            precio_actual = closes[-1]
            z_score = (precio_actual - sma) / std_dev

            true_ranges = [max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) for i in range(1, len(velas))]
            atr = sum(true_ranges[-14:]) / 14.0 if true_ranges else 0.0

            return z_score, atr, precio_actual
    except Exception:
        pass
    return None, None, None

def analizar_modelo_reversion(top_tokens):
    resultados = []
    
    for token in top_tokens:
        simbolo = token["symbol"]
        z_score, atr, precio = calcular_zscore_y_volatilidad(simbolo)
        obi, volumenes = obtener_datos_cuantitativos_libro(simbolo)
        
        if z_score is not None and obi is not None:
            alerta_reversion = None
            
            if z_score >= 2.2 and obi < -0.15:
                alerta_reversion = f"📉 OPORTUNIDAD DE REVERSIÓN A LA MEDIA (SHORT) | Z-Score: +{z_score:.2f}σ | OBI Estructural: {obi:.2f} (Absorción de Ask)"
            elif z_score <= -2.2 and obi > 0.15:
                alerta_reversion = f"📈 OPORTUNIDAD DE REVERSIÓN A LA MEDIA (LONG) | Z-Score: {z_score:.2f}σ | OBI Estructural: +{obi:.2f} (Absorción de Bid)"

            resultados.append({
                "symbol": simbolo,
                "change_hour": token["change_hour"],
                "price": precio,
                "z_score": z_score,
                "obi": obi,
                "bid_liquidity": volumenes["bids"],
                "ask_liquidity": volumenes["asks"],
                "reversion_signal": alerta_reversion
            })
            
    return resultados