# Experimento de prompts con qwen3.5:2b

32 textos del conjunto de desarrollo; solo tipos que busca la IA (PERSONA, DIRECCION, CONTRASENA).

| Variante | Precisión | Recall | F1 | Errores JSON | Segundos por texto |
| --- | --- | --- | --- | --- | --- |
| A. Lista única {tipo, texto} (v0.2) | 49 % | 79 % | 0.61 | 0 | 10.8 |
| B. Una lista por tipo | 88 % | 100 % | 0.94 | 0 | 5.0 |
| C. Una lista por tipo + ejemplo | 74 % | 97 % | 0.84 | 0 | 4.1 |
| D. Una lista por tipo + análisis previo | 100 % | 79 % | 0.88 | 0 | 7.2 |
| E. Texto libre (sin JSON obligatorio) | 100 % | 38 % | 0.55 | 0 | 1.7 |
