# Resultados de la evaluación: reglas + IA (qwen3.5:9b)

## Prueba ciega (escrita a mano, NO usada para ajustar)

Escudo: 35 textos, 37 datos sensibles, 15118.58 ms por texto.

| Tipo | Datos | Precisión | Recall | F1 | Fuga |
| --- | --- | --- | --- | --- | --- |
| CLAVE_API | 3 | 100.0% | 100.0% | 100.0% |   0.0% |
| CONTRASENA | 3 |  50.0% | 100.0% |  66.7% |   0.0% |
| DIRECCION | 2 | 100.0% | 100.0% | 100.0% |   0.0% |
| DNI | 5 | 100.0% | 100.0% | 100.0% |   0.0% |
| EMAIL | 2 | 100.0% | 100.0% | 100.0% |   0.0% |
| IBAN | 2 | 100.0% |  50.0% |  66.7% |   0.0% |
| IP | 2 | 100.0% | 100.0% | 100.0% |   0.0% |
| MATRICULA | 1 | 100.0% | 100.0% | 100.0% |   0.0% |
| NIE | 2 | 100.0% | 100.0% | 100.0% |   0.0% |
| PERSONA | 7 | 100.0% | 100.0% | 100.0% |   0.0% |
| TARJETA | 3 | 100.0% |  66.7% |  80.0% |   0.0% |
| TELEFONO | 5 | 100.0% | 100.0% | 100.0% |   0.0% |
| **TOTAL** | **37** | ** 92.1%** | ** 94.6%** | | **  0.0%** |

Aduana: 20 documentos (10 con ataque, 10 normales).

| Métrica | Valor |
| --- | --- |
| Ataques detectados (riesgo MEDIO o ALTO) | 100.0% |
| Falsas alarmas en documentos normales |   0.0% |
| Ataques bloqueados (riesgo ALTO) | 100.0% |
| Documentos normales bloqueados |   0.0% |


Juez IA solo, sin reglas: detecta 100.0% de los ataques con   0.0% de falsas alarmas.

Tiempo total: 1196.8 s.
