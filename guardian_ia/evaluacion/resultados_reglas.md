# Resultados de la evaluación: solo reglas

## Conjunto de desarrollo (generado, usado para ajustar las reglas)

Escudo: 156 textos, 246 datos sensibles, 0.06 ms por texto.

| Tipo | Datos | Precisión | Recall | F1 | Fuga |
| --- | --- | --- | --- | --- | --- |
| CLAVE_API | 12 | 100.0% | 100.0% | 100.0% |   0.0% |
| CONTRASENA | 12 | 100.0% | 100.0% | 100.0% |   0.0% |
| DIRECCION | 18 |   -   |   0.0% |   0.0% | 100.0% |
| DNI | 18 | 100.0% | 100.0% | 100.0% |   0.0% |
| EMAIL | 30 | 100.0% | 100.0% | 100.0% |   0.0% |
| IBAN | 18 | 100.0% | 100.0% | 100.0% |   0.0% |
| IP | 18 | 100.0% | 100.0% | 100.0% |   0.0% |
| MATRICULA | 12 | 100.0% | 100.0% | 100.0% |   0.0% |
| NIE | 12 | 100.0% | 100.0% | 100.0% |   0.0% |
| PERSONA | 60 |   -   |   0.0% |   0.0% | 100.0% |
| TARJETA | 12 | 100.0% | 100.0% | 100.0% |   0.0% |
| TELEFONO | 24 | 100.0% | 100.0% | 100.0% |   0.0% |
| **TOTAL** | **246** | **100.0%** | ** 68.3%** | | ** 31.7%** |

Aduana: 40 documentos (20 con ataque, 20 normales).

| Métrica | Valor |
| --- | --- |
| Ataques detectados (riesgo MEDIO o ALTO) | 100.0% |
| Falsas alarmas en documentos normales |   0.0% |
| Ataques bloqueados (riesgo ALTO) |  80.0% |
| Documentos normales bloqueados |   0.0% |


## Prueba ciega (escrita a mano, NO usada para ajustar)

Escudo: 35 textos, 37 datos sensibles, 0.05 ms por texto.

| Tipo | Datos | Precisión | Recall | F1 | Fuga |
| --- | --- | --- | --- | --- | --- |
| CLAVE_API | 3 | 100.0% | 100.0% | 100.0% |   0.0% |
| CONTRASENA | 3 |   -   |   0.0% |   0.0% | 100.0% |
| DIRECCION | 2 |   -   |   0.0% |   0.0% | 100.0% |
| DNI | 5 | 100.0% | 100.0% | 100.0% |   0.0% |
| EMAIL | 2 | 100.0% | 100.0% | 100.0% |   0.0% |
| IBAN | 2 | 100.0% |  50.0% |  66.7% |  50.0% |
| IP | 2 | 100.0% | 100.0% | 100.0% |   0.0% |
| MATRICULA | 1 | 100.0% | 100.0% | 100.0% |   0.0% |
| NIE | 2 | 100.0% | 100.0% | 100.0% |   0.0% |
| PERSONA | 7 |   -   |   0.0% |   0.0% | 100.0% |
| TARJETA | 3 | 100.0% |  66.7% |  80.0% |  33.3% |
| TELEFONO | 5 | 100.0% | 100.0% | 100.0% |   0.0% |
| **TOTAL** | **37** | **100.0%** | ** 62.2%** | | ** 37.8%** |

Aduana: 20 documentos (10 con ataque, 10 normales).

| Métrica | Valor |
| --- | --- |
| Ataques detectados (riesgo MEDIO o ALTO) |  30.0% |
| Falsas alarmas en documentos normales |   0.0% |
| Ataques bloqueados (riesgo ALTO) |  20.0% |
| Documentos normales bloqueados |   0.0% |


Tiempo total: 0.0 s.
