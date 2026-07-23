Markdown
<div align="center">

# ⚡ Quant Market Alerts Bot

> **Sistema automatizado de monitoreo cuantitativo y alertas de mercado en tiempo real.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?style=for-the-badge&logo=flask&logoColor=black)](https://flask.palletsprojects.com/)
[![Render](https://img.shields.io/badge/Render-Deployed-success?style=for-the-badge&logo=render&logoColor=white)](https://render.com/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue?style=for-the-badge&logo=telegram&logoColor=white)](https://telegram.org/)

</div>

---

## 🚀 Sobre el Proyecto

**Quant Market Alerts Bot** es una herramienta de trading cuantitativo diseñada para escanear de manera autónoma los activos del mercado, procesar modelos matemáticos y estadísticos de reversión y liquidaciones, y despachar alertas automatizadas directamente a un canal o chat de Telegram. 

El sistema corre de forma ininterrumpida 24/7 en la nube mediante un servicio web en Render sincronizado con un planificador de tareas interno.

---

## ✨ Características Principales

* **🕒 Escaneo Automatizado:** Ejecución programada cada hora mediante `APScheduler` para evaluar las condiciones del mercado sin intervención manual.
* **📱 Alertas en Tiempo Real:** Envío inmediato de señales de alta probabilidad directo a Telegram.
* **🛡️ Arquitectura Robusta:** Diseñado bajo un patrón modular con separación de responsabilidades entre el servidor web y los motores de análisis cuantitativo.
* **☁️ Alta Disponibilidad:** Desplegado en la nube con soporte para servidores WSGI (Gunicorn) y endpoints de control de estado (*health check*).

---

## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python
* **Framework Web:** Flask
* **Planificación:** APScheduler & Pytz
* **Despliegue & Servidor:** Render & Gunicorn
* **Control de Versiones:** Git / GitHub (`allan230807`)

---

## 📂 Estructura del Repositorio

```text
alerts-bot/
│
├── core/
│   ├── __init__.py
│   ├── bot_server.py        # Motor principal de análisis cuantitativo
│   ├── liquidations.py      # Modelos de análisis de liquidaciones y reversión
│   ├── scanner.py           # Escáner de mercado
│   └── users_db.py          # Gestión de base de datos / usuarios
│
├── .env                     # Variables de entorno locales (Privado)
├── .gitignore
├── app.py                   # Servidor web Flask y programador de tareas (Scheduler)
├── README.md                # Documentación del proyecto
└── requirements.txt         # Dependencias del proyecto
