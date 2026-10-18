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
3. Desactivar antes de tiempo: agrega el ID (8 hex) a `SCHEDORA_REVOCADOS` en Render
   (separado por comas); Render reinicia y el acceso deja de funcionar.
4. El acceso vence al final del día (zona `SCHEDORA_TZ`, por defecto America/Hermosillo).
Sin `SCHEDORA_SECRET` la app **no deja entrar a nadie** (solo `SCHEDORA_ACCESO_ABIERTO=1`, para pruebas locales).

## Render
Sube el repositorio a GitHub → Render: *New → Blueprint* (usa `render.yaml`) → define
`SCHEDORA_SECRET` en Environment. Plan gratis: se duerme sin uso y no guarda archivos
(por diseño, no se guarda nada de los clientes).

## Variables
`SCHEDORA_SECRET`, `SCHEDORA_REVOCADOS`, `SCHEDORA_TZ`, `SCHEDORA_MAX_SIMULTANEAS` (2),
`SCHEDORA_MAX_SEGUNDOS` (60), `SCHEDORA_ACCESO_ABIERTO` (solo local).

## Fuera de esta versión
Salones, sesiones fijas, límites por oferta, base de datos y cobros automáticos.
Ver `docs/`.
