# Relatorio de Reconstrucao

Gerado em 2026-07-03T22:18:44 | 8 sinais por servidor (mesma sequencia).


## Servidor PYTHON

| # | sinal | algoritmo | ganho | pixels | iter | inicio | fim | solver (ms) | imagem |
|--:|-------|-----------|:-----:|-------:|:----:|--------|-----|------------:|--------|
| 1 | A-60x60-1.csv | CGNE_PYTHON | sim | 3600 | 10 | 22:18:18.214 | 22:18:19.202 | 988.0 | [python_01_CGNE.png](imagens/python_01_CGNE.png) |
| 1 | A-60x60-1.csv | CGNR_PYTHON | sim | 3600 | 10 | 22:18:20.277 | 22:18:21.272 | 995.0 | [python_01_CGNR.png](imagens/python_01_CGNR.png) |
| 2 | A-30x30-1.csv | CGNE_PYTHON | sim | 900 | 10 | 22:18:21.724 | 22:18:21.952 | 227.4 | [python_02_CGNE.png](imagens/python_02_CGNE.png) |
| 2 | A-30x30-1.csv | CGNR_PYTHON | sim | 900 | 10 | 22:18:22.031 | 22:18:22.191 | 160.4 | [python_02_CGNR.png](imagens/python_02_CGNR.png) |
| 3 | A-60x60-1.csv | CGNE_PYTHON | sim | 3600 | 10 | 22:18:22.508 | 22:18:23.499 | 991.4 | [python_03_CGNE.png](imagens/python_03_CGNE.png) |
| 3 | A-60x60-1.csv | CGNR_PYTHON | sim | 3600 | 10 | 22:18:23.605 | 22:18:24.601 | 995.9 | [python_03_CGNR.png](imagens/python_03_CGNR.png) |
| 4 | G-2.csv | CGNE_PYTHON | sim | 3600 | 10 | 22:18:24.923 | 22:18:25.908 | 985.2 | [python_04_CGNE.png](imagens/python_04_CGNE.png) |
| 4 | G-2.csv | CGNR_PYTHON | sim | 3600 | 10 | 22:18:26.017 | 22:18:27.009 | 991.7 | [python_04_CGNR.png](imagens/python_04_CGNR.png) |
| 5 | g-30x30-1.csv | CGNE_PYTHON | sim | 900 | 10 | 22:18:27.230 | 22:18:27.381 | 150.8 | [python_05_CGNE.png](imagens/python_05_CGNE.png) |
| 5 | g-30x30-1.csv | CGNR_PYTHON | sim | 900 | 10 | 22:18:27.463 | 22:18:27.630 | 166.9 | [python_05_CGNR.png](imagens/python_05_CGNR.png) |
| 6 | g-30x30-2.csv | CGNE_PYTHON | sim | 900 | 10 | 22:18:27.932 | 22:18:28.080 | 148.0 | [python_06_CGNE.png](imagens/python_06_CGNE.png) |
| 6 | g-30x30-2.csv | CGNR_PYTHON | sim | 900 | 10 | 22:18:28.159 | 22:18:28.310 | 151.1 | [python_06_CGNR.png](imagens/python_06_CGNR.png) |
| 7 | A-60x60-1.csv | CGNE_PYTHON | nao | 3600 | 10 | 22:18:28.516 | 22:18:29.482 | 966.2 | [python_07_CGNE.png](imagens/python_07_CGNE.png) |
| 7 | A-60x60-1.csv | CGNR_PYTHON | nao | 3600 | 10 | 22:18:29.606 | 22:18:30.656 | 1049.5 | [python_07_CGNR.png](imagens/python_07_CGNR.png) |
| 8 | G-2.csv | CGNE_PYTHON | nao | 3600 | 3 | 22:18:31.050 | 22:18:31.356 | 306.0 | [python_08_CGNE.png](imagens/python_08_CGNE.png) |
| 8 | G-2.csv | CGNR_PYTHON | nao | 3600 | 3 | 22:18:31.463 | 22:18:31.778 | 315.4 | [python_08_CGNR.png](imagens/python_08_CGNR.png) |

**Soma solver:** 9588.7 ms | **Medio:** 599.3 ms | **Throughput:** 1.7 img/s


## Servidor CPP_OPENMP

| # | sinal | algoritmo | ganho | pixels | iter | inicio | fim | solver (ms) | imagem |
|--:|-------|-----------|:-----:|-------:|:----:|--------|-----|------------:|--------|
| 1 | A-60x60-1.csv | CGNE_CPP | sim | 3600 | 10 | 22:18:34.105 | 22:18:34.842 | 736.1 | [cpp_openmp_01_CGNE.png](imagens/cpp_openmp_01_CGNE.png) |
| 1 | A-60x60-1.csv | CGNR_CPP | sim | 3600 | 10 | 22:18:34.950 | 22:18:35.724 | 774.2 | [cpp_openmp_01_CGNR.png](imagens/cpp_openmp_01_CGNR.png) |
| 2 | A-30x30-1.csv | CGNE_CPP | sim | 900 | 10 | 22:18:36.159 | 22:18:36.264 | 105.5 | [cpp_openmp_02_CGNE.png](imagens/cpp_openmp_02_CGNE.png) |
| 2 | A-30x30-1.csv | CGNR_CPP | sim | 900 | 10 | 22:18:36.347 | 22:18:36.461 | 114.5 | [cpp_openmp_02_CGNR.png](imagens/cpp_openmp_02_CGNR.png) |
| 3 | A-60x60-1.csv | CGNE_CPP | sim | 3600 | 10 | 22:18:36.776 | 22:18:37.552 | 776.0 | [cpp_openmp_03_CGNE.png](imagens/cpp_openmp_03_CGNE.png) |
| 3 | A-60x60-1.csv | CGNR_CPP | sim | 3600 | 10 | 22:18:37.674 | 22:18:38.483 | 808.6 | [cpp_openmp_03_CGNR.png](imagens/cpp_openmp_03_CGNR.png) |
| 4 | G-2.csv | CGNE_CPP | sim | 3600 | 10 | 22:18:38.813 | 22:18:39.624 | 811.7 | [cpp_openmp_04_CGNE.png](imagens/cpp_openmp_04_CGNE.png) |
| 4 | G-2.csv | CGNR_CPP | sim | 3600 | 10 | 22:18:39.750 | 22:18:40.487 | 737.3 | [cpp_openmp_04_CGNR.png](imagens/cpp_openmp_04_CGNR.png) |
| 5 | g-30x30-1.csv | CGNE_CPP | sim | 900 | 10 | 22:18:40.698 | 22:18:40.805 | 107.2 | [cpp_openmp_05_CGNE.png](imagens/cpp_openmp_05_CGNE.png) |
| 5 | g-30x30-1.csv | CGNR_CPP | sim | 900 | 10 | 22:18:40.889 | 22:18:40.997 | 108.1 | [cpp_openmp_05_CGNR.png](imagens/cpp_openmp_05_CGNR.png) |
| 6 | g-30x30-2.csv | CGNE_CPP | sim | 900 | 10 | 22:18:41.284 | 22:18:41.390 | 106.4 | [cpp_openmp_06_CGNE.png](imagens/cpp_openmp_06_CGNE.png) |
| 6 | g-30x30-2.csv | CGNR_CPP | sim | 900 | 10 | 22:18:41.474 | 22:18:41.582 | 107.9 | [cpp_openmp_06_CGNR.png](imagens/cpp_openmp_06_CGNR.png) |
| 7 | A-60x60-1.csv | CGNE_CPP | nao | 3600 | 10 | 22:18:41.783 | 22:18:42.511 | 728.2 | [cpp_openmp_07_CGNE.png](imagens/cpp_openmp_07_CGNE.png) |
| 7 | A-60x60-1.csv | CGNR_CPP | nao | 3600 | 10 | 22:18:42.637 | 22:18:43.412 | 775.1 | [cpp_openmp_07_CGNR.png](imagens/cpp_openmp_07_CGNR.png) |
| 8 | G-2.csv | CGNE_CPP | nao | 3600 | 3 | 22:18:43.805 | 22:18:44.020 | 214.6 | [cpp_openmp_08_CGNE.png](imagens/cpp_openmp_08_CGNE.png) |
| 8 | G-2.csv | CGNR_CPP | nao | 3600 | 3 | 22:18:44.141 | 22:18:44.356 | 214.8 | [cpp_openmp_08_CGNR.png](imagens/cpp_openmp_08_CGNR.png) |

**Soma solver:** 7226.0 ms | **Medio:** 451.6 ms | **Throughput:** 2.2 img/s


## Comparacao Python x C++

| metrica | Python | C++ | mais rapido |
|---------|-------:|----:|:-----------:|
| solver medio (ms) | 599.3 | 451.6 | C++ |
| throughput (img/s) | 1.7 | 2.2 | C++ |

**C++ foi 1.33x mais rapido que o Python neste teste.**
