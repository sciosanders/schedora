# Modelo de datos (Excel)
Hojas: PROFESORES, MATERIAS, OFERTA_ACADEMICA, DISPONIBILIDAD, CONFIGURACION.
Descarga la plantilla desde la app: trae hoja INSTRUCCIONES y listas desplegables.
- Calendario por defecto: lunes a sábado, 07:00–18:00, sesiones de 1 o 2 h, solo horas en punto.
- Disponibilidad: sin filas = libre todo el calendario; filas DISPONIBLE = lista blanca;
  solo NO_DISPONIBLE = calendario menos esas franjas; NO_DISPONIBLE prevalece.
- Continuidad docente: peso 1/(1+horas_objetivo).
- Estados: LISTO, SIN_SOLUCION (infactible demostrado), INCONCLUSO (sin tiempo, no es "imposible"),
  ENTRADA_INVALIDA, NO_VERIFICADO (el verificador independiente rechazó el horario; no se exporta), ERROR.
