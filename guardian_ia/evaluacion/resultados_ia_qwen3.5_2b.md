# Resultados de la evaluación: reglas + IA (qwen3.5:2b)

## Conjunto de desarrollo (generado, usado para ajustar las reglas)

Escudo: 156 textos, 246 datos sensibles, 6378.88 ms por texto.

| Tipo | Datos | Precisión | Recall | F1 | Fuga |
| --- | --- | --- | --- | --- | --- |
| CLAVE_API | 12 | 100.0% | 100.0% | 100.0% |   0.0% |
| CONTRASENA | 12 |  75.0% | 100.0% |  85.7% |   0.0% |
| DIRECCION | 18 |  81.8% | 100.0% |  90.0% |   0.0% |
| DNI | 18 | 100.0% | 100.0% | 100.0% |   0.0% |
| EMAIL | 30 | 100.0% | 100.0% | 100.0% |   0.0% |
| IBAN | 18 | 100.0% | 100.0% | 100.0% |   0.0% |
| IP | 18 | 100.0% | 100.0% | 100.0% |   0.0% |
| MATRICULA | 12 | 100.0% | 100.0% | 100.0% |   0.0% |
| NIE | 12 | 100.0% | 100.0% | 100.0% |   0.0% |
| PERSONA | 60 | 100.0% |  98.3% |  99.2% |   1.7% |
| TARJETA | 12 | 100.0% | 100.0% | 100.0% |   0.0% |
| TELEFONO | 24 | 100.0% | 100.0% | 100.0% |   0.0% |
| **TOTAL** | **246** | ** 96.8%** | ** 99.6%** | | **  0.4%** |

Aduana: 40 documentos (20 con ataque, 20 normales).

| Métrica | Valor |
| --- | --- |
| Ataques detectados (riesgo MEDIO o ALTO) | 100.0% |
| Falsas alarmas en documentos normales |   0.0% |
| Ataques bloqueados (riesgo ALTO) |  80.0% |
| Documentos normales bloqueados |   0.0% |


Juez IA solo, sin reglas: detecta  45.0% de los ataques con   0.0% de falsas alarmas.

## Prueba ciega (escrita a mano, NO usada para ajustar)

Escudo: 35 textos, 37 datos sensibles, 3897.43 ms por texto.

| Tipo | Datos | Precisión | Recall | F1 | Fuga |
| --- | --- | --- | --- | --- | --- |
| CLAVE_API | 3 | 100.0% | 100.0% | 100.0% |   0.0% |
| CONTRASENA | 3 |  50.0% | 100.0% |  66.7% |   0.0% |
| DIRECCION | 2 | 100.0% | 100.0% | 100.0% |   0.0% |
| DNI | 5 | 100.0% | 100.0% | 100.0% |   0.0% |
| EMAIL | 2 | 100.0% | 100.0% | 100.0% |   0.0% |
| IBAN | 2 | 100.0% |  50.0% |  66.7% |  50.0% |
| IP | 2 | 100.0% | 100.0% | 100.0% |   0.0% |
| MATRICULA | 1 | 100.0% | 100.0% | 100.0% |   0.0% |
| NIE | 2 | 100.0% | 100.0% | 100.0% |   0.0% |
| PERSONA | 7 | 100.0% | 100.0% | 100.0% |   0.0% |
| TARJETA | 3 | 100.0% |  66.7% |  80.0% |   0.0% |
| TELEFONO | 5 | 100.0% | 100.0% | 100.0% |   0.0% |
| **TOTAL** | **37** | ** 92.1%** | ** 94.6%** | | **  2.7%** |

Aduana: 20 documentos (10 con ataque, 10 normales).

| Métrica | Valor |
| --- | --- |
| Ataques detectados (riesgo MEDIO o ALTO) |  50.0% |
| Falsas alarmas en documentos normales |   0.0% |
| Ataques bloqueados (riesgo ALTO) |  40.0% |
| Documentos normales bloqueados |   0.0% |


Juez IA solo, sin reglas: detecta  50.0% de los ataques con   0.0% de falsas alarmas.

Tiempo total: 1659.6 s.
