# Experimento de prompts con qwen3.5:9b

32 textos del conjunto de desarrollo; solo tipos que busca la IA (PERSONA, DIRECCION, CONTRASENA).

| Variante | Precisión | Recall | F1 | Errores JSON | Segundos por texto |
| --- | --- | --- | --- | --- | --- |
| A. Lista única {tipo, texto} (v0.2) | 67 % | 76 % | 0.71 | 0 | 18.8 |
| B. Una lista por tipo | 91 % | 100 % | 0.95 | 0 | 17.4 |
| D. Una lista por tipo + análisis previo | 94 % | 100 % | 0.97 | 0 | 27.7 |
