#!/usr/bin/env bash
# Crea el App Service de Schedora con Azure CLI. Revísalo y edita las variables antes de ejecutar.
#   az login && bash infra/azure.sh
set -euo pipefail

GRUPO="${GRUPO:-rg-schedora}"
UBICACION="${UBICACION:-westus3}"          # elige la región más cercana a tus clientes
PLAN="${PLAN:-plan-schedora}"
APP="${APP:?Define APP con un nombre único global, p. ej. APP=schedora-gtu}"
SKU="${SKU:-B1}"                            # B1 o superior: permite Always On. F1/gratis NO es recomendable.
SECRETO="${SCHEDORA_SECRET:?Define SCHEDORA_SECRET (≥16 caracteres, aleatorio)}"

az group create -n "$GRUPO" -l "$UBICACION"
az appservice plan create -g "$GRUPO" -n "$PLAN" --is-linux --sku "$SKU"
az webapp create -g "$GRUPO" -p "$PLAN" -n "$APP" --runtime "PYTHON:3.12"

# Configuración general
az webapp config set -g "$GRUPO" -n "$APP" \
  --startup-file "python app.py" \
  --always-on true \
  --web-sockets-enabled true \
  --http20-enabled true \
  --min-tls-version 1.2 \
  --generic-configurations '{"healthCheckPath": "/"}'
az webapp update -g "$GRUPO" -n "$APP" --https-only true

# Variables de entorno (App Settings). Cambiarlas reinicia la app.
az webapp config appsettings set -g "$GRUPO" -n "$APP" --settings \
  SCM_DO_BUILD_DURING_DEPLOYMENT=true \
  WEBSITES_PORT=8000 \
  SCHEDORA_SECRET="$SECRETO" \
  SCHEDORA_REVOCADOS="" \
  SCHEDORA_TZ=America/Hermosillo \
  SCHEDORA_MAX_SIMULTANEAS=2 \
  SCHEDORA_MAX_SEGUNDOS=60 \
  GRADIO_ANALYTICS_ENABLED=False \
  >/dev/null

echo "Listo: https://${APP}.azurewebsites.net"
echo "Siguiente: agrega en GitHub el secreto AZURE_WEBAPP_PUBLISH_PROFILE y la variable AZURE_WEBAPP_NAME=${APP}"
