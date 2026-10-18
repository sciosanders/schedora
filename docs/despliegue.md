# Despliegue en Azure App Service (Linux) y plan v1.2

## Decisiones
- Pagos manuales; sin base de datos; acceso por código firmado (HMAC) con caducidad.
- Al no guardar estado, funciona con varias instancias sin cambios.
- Plan **B1 o superior**: permite *Always On* y CPU estable. El plan gratuito (F1) limita CPU por día y duerme la app; no sirve para el optimizador.
- La app escucha en `WEBSITES_PORT` (8000) y arranca con `python app.py` (Gradio incluye su servidor).

## Pasos
1. Crear recursos: `infra/azure.sh` (lee el script antes; usa Azure CLI).
2. Habilitar WebSockets y Always On (el script lo hace). Health check en `/`.
3. Secretos: lo ideal es guardar `SCHEDORA_SECRET` en Key Vault y referenciarlo en la variable
   como `@Microsoft.KeyVault(SecretUri=https://<vault>.vault.azure.net/secrets/schedora-secret/)`
   (requiere identidad administrada con permiso de lectura). El código no cambia.
4. GitHub → Settings → Secrets: `AZURE_WEBAPP_PUBLISH_PROFILE` (descargar perfil de publicación en el portal;
   requiere "Basic authentication" habilitada para SCM). Escribe el nombre de tu app en `app-name` de `.github/workflows/deploy.yml`.
   Alternativa más segura: OIDC con `azure/login`.
5. Push a `main`: despliegue (las pruebas corren en `ci.yml`; Azure compila dependencias por `SCM_DO_BUILD_DURING_DEPLOYMENT`).
6. Ver errores: *Monitoreo → Log stream*.

## Operación de accesos
Crear códigos con `python admin.py` en tu equipo (mismo `SCHEDORA_SECRET`). Revocar: editar `SCHEDORA_REVOCADOS`
(reinicia la app). Un acceso vence al final del día en `SCHEDORA_TZ`.

## Pendiente
Salones, sesiones fijas, límites por oferta, base de datos y pagos automáticos, aviso de privacidad y términos,
dominio propio con certificado, alertas en Application Insights.
