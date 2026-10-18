# Schedora

Generador automático de horarios docentes. Sube tu Excel, revisa, genera y descarga.
Acceso por códigos temporales (pago manual): tú creas y desactivas cada acceso.

> **Importante:** el optimizador (OR-Tools) y la interfaz (Gradio) se escribieron en un entorno
> donde no se podían instalar paquetes, así que **no se han ejecutado todavía**. El resto
> (lectura de Excel, validaciones, verificador de horarios, exportación, códigos de acceso,
> callbacks) sí se probó. Tu primer paso:
>
> ```bash
> python -m venv .venv && source .venv/bin/activate
> pip install -r requirements-dev.txt
> pytest          # deben pasar también las pruebas del optimizador
> SCHEDORA_ACCESO_ABIERTO=1 python app.py   # http://localhost:7860
> ```
> Si algo falla, probablemente sea un detalle de versión de Gradio u OR-Tools: avísame con el error.
> Después de la primera corrida buena, ejecuta `pip freeze` y fija versiones.

## Códigos de acceso temporales
1. Define un secreto largo (≥16 caracteres) y **nunca lo subas a GitHub**:
   `export SCHEDORA_SECRET="..."`
2. Crear un acceso de 5 días: `python admin.py crear --escuela "Escuela X" --dias 5`
   (queda registrado en `accesos.csv`, ignorado por git). Envía el código al cliente.
3. Desactivar antes de tiempo: agrega el ID (8 hex) a `SCHEDORA_REVOCADOS` en Azure
   (separado por comas); Azure reinicia y el acceso deja de funcionar.
4. El acceso vence al final del día (zona `SCHEDORA_TZ`, por defecto America/Hermosillo).
Sin `SCHEDORA_SECRET` la app **no deja entrar a nadie** (solo `SCHEDORA_ACCESO_ABIERTO=1`, para pruebas locales).

## Despliegue en Azure App Service (Linux)
Guía completa en `docs/despliegue.md`. Resumen:
1. `APP=mi-app-unica SCHEDORA_SECRET="..." bash infra/azure.sh` crea grupo, plan B1, web app (Python 3.11) y variables.
2. En GitHub: secreto `AZURE_WEBAPP_PUBLISH_PROFILE` y variable `AZURE_WEBAPP_NAME`; cada push a `main` corre las pruebas y despliega.
3. Revocar un acceso: agrega su ID a `SCHEDORA_REVOCADOS` en *Configuración → Variables de entorno* (la app se reinicia).

## Variables de entorno
| Variable | Uso |
|---|---|
| `SCHEDORA_SECRET` | Secreto de firma (≥16 caracteres). Obligatoria. Mejor como referencia a Key Vault. |
| `SCHEDORA_REVOCADOS` | IDs de acceso desactivados, separados por coma. |
| `SCHEDORA_TZ` | Zona horaria del vencimiento (America/Hermosillo). |
| `SCHEDORA_MAX_SIMULTANEAS` / `SCHEDORA_MAX_SEGUNDOS` | Generaciones simultáneas (2) y tope de búsqueda en segundos (60). |
| `SCHEDORA_ACCESO_ABIERTO` | Solo local. En Azure se ignora. |
| `WEBSITES_PORT` | Puerto interno (8000) que Azure enruta a la app. |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true`: Azure instala `requirements.txt` al desplegar. |
| `GRADIO_ANALYTICS_ENABLED` | `False`. |

## Fuera de esta versión
Salones, sesiones fijas, límites por oferta, base de datos y cobros automáticos.
Ver `docs/`.
