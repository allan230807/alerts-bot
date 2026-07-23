# Quant Bot - Proyecto Cuantitativo de Futuros

Bot de análisis cuantitativo en Python para mercados de criptomonedas (Binance Futures), diseñado para procesar métricas como Z-Score, OBI (Order Book Imbalance) y simulaciones de Monte Carlo, enviando alertas automatizadas a Telegram cada 15 minutos.

## Estado del Proyecto: En Pausa / Archivado

El despliegue automatizado de este bot se encuentra detenido y el workflow de GitHub Actions ha sido deshabilitado. 

## ¿Qué nos detuvo? (Obstáculos Técnicos)

Durante el proceso de configuración en la nube, nos topamos con una serie de bloqueos técnicos insalvables bajo esquemas gratuitos:

1. **Restricciones Geográficas (Geoblocking):**
   - Bybit y Binance prohíben el acceso a sus APIs desde direcciones IP ubicadas en Estados Unidos.
   - Los servidores donde corre GitHub Actions se encuentran en EE. UU., lo que generaba errores constantes de conexión al intentar consultar los endpoints de futuros (`fapi`).

2. **Barreras en Infraestructuras Cloud Gratuitas:**
   - **Render y AWS Lambda:** Exigen tarjetas de crédito bancarias tradicionales para la verificación de identidad a través de pasarelas de pago, descartando y rechazando tarjetas virtuales o prepagadas (como Zinli).
   - **Hugging Face Spaces:** Modificó sus políticas de uso gratuito, limitando el cómputo a páginas estáticas y cobrando por la ejecución de entornos de backend en Python.
   - **Proxies públicos:** Descartados por su alta inestabilidad y porque los sistemas de seguridad (WAF/Cloudflare) de los exchanges terminan bloqueándolos de inmediato.

## Conclusión

El código base y la lógica cuantitativa desarrollada se mantienen seguros en el repositorio. Hoy el proyecto queda pausado para avanzar hacia un nuevo objetivo.
