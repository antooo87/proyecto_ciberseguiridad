# Casos reales y difíciles

Una empresa **inventada**, «Cierzo Rutas y Almacenes, S.L.» (logística, Zaragoza), con los documentos que tendría
de verdad en su ordenador. Sirven para enseñar el Guardián con ejemplos densos (no con frases de una línea) y para
comprobar que ninguna mejora rompe lo que ya funciona (`tests/test_casos_reales.py`).

Todo es inventado: personas, DNI (con su letra correcta, para que parezcan reales), cuentas, teléfonos y webs
(`.example` y `.top`). Los archivos los crea `generar.py`, que apunta cada dato que mete y guarda en
`esperado.json` lo que tiene que encontrar el Guardián en cada uno.

> **Ojo:** estos casos se escribieron a la vez que se mejoraban las reglas, así que **no son una medida a ciegas**
> (esa está en `evaluacion/`). Al probarlos aparecieron fallos de verdad que se arreglaron: el NSS en una columna de
> Excel, la contraseña dentro de una cadena de conexión, los correos .eml leídos «a pelo» y seis preguntas mal
> entendidas por «Mejorar mi pregunta».

## Qué hay y qué tiene que salir

### 1. `1_carpeta_rrhh/`: ¿puedo darle esta carpeta a una IA?

```
python -m guardian escanear ejemplos/casos_reales/1_carpeta_rrhh
```

| Archivo | Qué es | Veredicto |
| --- | --- | --- |
| `nominas_noviembre_2026.xlsx` | 15 nóminas con DNI/NIE, Seguridad Social e IBAN + una hoja **muy oculta** que ordena a la IA mandar los IBAN a una web | TRAMPA (45 datos) |
| `cv_candidato_ciberseguridad.docx` | currículum con una orden en texto **oculto de Word** y otra en **letra blanca de 1 pt** | TRAMPA |
| `formacion_phishing_2026.pptx` | formación con una **diapositiva oculta** que dice a la IA que el examen es opcional | TRAMPA |
| `encuesta_clima_laboral_2026.xlsx` | encuesta con una orden en una celda con formato **;;;** (no enseña su valor) y una fila oculta | TRAMPA |
| `portal_empleado_intranet.html` | intranet con un bloque **display:none**, un comentario HTML y una **imagen espía** para robar la contraseña | TRAMPA |
| `organigrama_2027.docx` | Word que al abrirse descarga una **plantilla remota** de Internet | TRAMPA |
| `asistentes_curso_prl.csv` | 15 asistentes con DNI/NIE, correo y móvil | DATOS (45 datos) |
| `contrato_indefinido_lasheras.docx` | contrato con DNI, CIF, NSS, fecha de nacimiento, IBAN, teléfono y correos | DATOS (9 datos) |
| `correo_cambio_cuenta_nomina.eml` | el fraude de la nómina: «ingresadme la nómina en esta cuenta nueva» | DATOS |
| `credenciales_servidor_nominas.txt` | contraseñas (una dentro de `postgres://usuario:clave@...`), clave de API, token e IP | DATOS |
| `parte_baja_moreno.pdf` | parte de baja con DNI, NSS, fecha de nacimiento y teléfono | DATOS |
| `bienvenida_nuevos_empleados.pptx` | presentación con una diapositiva azul y letra blanca (**se ve**: no es trampa) | LIMPIO |
| `politica_teletrabajo_2026.pdf` | política de 2 páginas con franja oscura y título blanco | LIMPIO |
| `acta_comite_seguridad.txt` | acta de una reunión | LIMPIO |
| `dni_escaneado_lasheras.png` | una imagen: el Guardián **no lee imágenes** y lo dice («1 archivo sin revisar») | – |

Después, para compartir uno: `python -m guardian anonimizar ejemplos/casos_reales/1_carpeta_rrhh/contrato_indefinido_lasheras.docx`.

### 2. `2_contrato_largo/`: anonimizar un contrato de verdad

Contrato de mantenimiento informático entre dos empresas: 51 datos (DNI, NIE, CIF, IBAN, teléfonos, correos, IP de
los servidores, matrículas de las furgonetas de los técnicos) repartidos en cláusulas, tablas y anexos.

```
python -m guardian anonimizar ejemplos/casos_reales/2_contrato_largo/contrato_mantenimiento_cierzo_datanorte.docx
```

Tiene que tapar **los 51** y no dejar ni uno (lo comprueba el test). Sin la IA local no tapa los nombres ni las
direcciones: para eso está la detección con IA (`--ia`).

### 3. `3_bandeja_de_entrada/`: ¿cuáles son estafas?

13 correos guardados como .eml (como los guarda Outlook o Gmail): 10 estafas y 3 normales.

```
python -m guardian estafa --carpeta ejemplos/casos_reales/3_bandeja_de_entrada
python -m guardian estafa --archivo ejemplos/casos_reales/3_bandeja_de_entrada/13_boletin_con_aviso_escondido.eml
```

| Correo | Lo que lo delata |
| --- | --- |
| Correos: paquete retenido | el enlace dice `www.correos.es` pero lleva a `correos-envios.top`; el remitente no es de correos.es |
| Santander: cuenta bloqueada | remitente y enlace que imitan al banco, amenaza, pide DNI y claves |
| Hacienda: devolución | dominio `.com` raro, enlace acortado, pide datos bancarios |
| Director: transferencia urgente | cambio de cuenta + prisa + secreto, y **las respuestas van a otra dirección** |
| Microsoft 365: contraseña caduca | botón que lleva a un dominio que imita a Microsoft |
| Oferta de trabajo desde casa | dinero fácil por dar «me gusta» y te lleva a WhatsApp |
| Sextorsión | chantaje con un vídeo que no existe |
| Factura pendiente | adjunto `Factura_FAC-2026-1187.pdf.iso`: **un programa disfrazado de PDF** |
| DGT: multa | dominio que no es dgt.es, prisa y amenaza de embargo |
| Boletín del club ciclista | **texto escondido** (tamaño 0, blanco) que ordena a la IA que resume el correo decir que te han robado la contraseña: el truco que se descubrió en 2025 con Gemini en Gmail |
| Amazon, un compañero, BBVA | correos normales: no salta nada |

En la web: «¿Es una estafa?» → pestaña «Varios correos (.eml)» → «Probar con una bandeja de ejemplo».

### 4. `4_respuestas_de_ia/`: ¿me fío de lo que me ha dicho la IA?

```
python -m guardian verificar --archivo ejemplos/casos_reales/4_respuestas_de_ia/01_instalar_herramienta.txt
```

| Respuesta | Nivel |
| --- | --- |
| `01_instalar_herramienta.txt`: `curl ... \| sudo bash`, `chmod -R 777 /`, `irm ... \| iex` | PELIGRO |
| `02_acelerar_pc.txt`: desactivar el antivirus y el cortafuegos, tarea que arranca sola | PELIGRO |
| `03_resumen_manipulado.txt`: te pide la contraseña, enlace que imita a BBVA e imagen que se lleva tus datos | PELIGRO |
| `04_codigo_con_secretos.txt`: código con una clave de API y un IBAN que tú no le diste | AVISO |
| `05_texto_invisible.txt`: un mensaje escrito con letras invisibles (etiquetas Unicode) | AVISO |
| `06_respuesta_correcta.txt`: cómo activar la verificación en dos pasos, con la web oficial | OK |

### 5. `5_preguntas_vagas.txt`: preguntas como las escribe la gente

Diez preguntas mal hechas a propósito («hazme un correo para mi jefe», «no me funciona el excel desde ayer»...).
Pruébalas en la web («✨ Mejorar mi pregunta») o en la terminal:

```
python -m guardian mejorar "hazme un correo para mi jefe"
```

La última lleva un DNI y un IBAN: se tapan antes de nada.

## Volver a crearlos

```
python ejemplos/casos_reales/generar.py
```

Siempre crea exactamente los mismos archivos (mismas fechas dentro de los zip), así que el test puede comprobar que
los del repositorio están al día.
