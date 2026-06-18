# Reconstrução de Imagem de Ultrassom (CGNE / CGNR)

Projeto APS de Sistemas Distribuídos: reconstrução de imagem de ultrassom com
**duas versões do servidor** — **Python** (interpretada) e **C++** (compilada).

**Comece pela apresentação: [APRESENTACAO.md](APRESENTACAO.md)** — o trabalho:
algoritmos, requisitos, resultados (com todas as imagens reconstruídas).

**Extras + glossário: [EXTRAS_E_GLOSSARIO.md](EXTRAS_E_GLOSSARIO.md)** — a análise
de baixo nível, o experimento de memória (tetos agressivos) e o dicionário de
termos (GEMV, BLAS, …). Os experimentos extra ficam na subpasta `extras/`.

## Execução rápida

```powershell
pip install -r requirements.txt
python preparar_dados.py        # descompacta H e gera caches (.npy / .bin)
./compilar.ps1                  # compila os programas C++ (g++ do MSYS2/MinGW)
python cliente.py --servidor ambos --n 8   # cliente + relatório
python bench_throughput.py      # desempenho: Python vs C++ (OpenBLAS) vs C++ (OpenMP)
python gerar_figuras.py         # gera todas as figuras
# experimentos extra:
python extras/experimento_memoria.py   # pouca memória (streaming + float32)
python extras/simular_pouca_ram.py     # servidor com pouca RAM (teto real)
```

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `algoritmos.py` | CGNE + CGNR, ganho, carga de dados, salvar imagem (núcleo do projeto) |
| `servidor_python.py` | servidor interpretado (Python) |
| `servidor_cpp.cpp` | servidor compilado (C++) |
| `cliente.py` | envia os sinais, gera o relatório e compara as duas versões |
| `operacoes_basicas.py` / `.cpp` | atividade 2 (MN, aM, Ma) |
| `preparar_dados.py` | descompacta H e cria os caches |
| `bench_throughput.py` | compara desempenho: Python vs C++ (OpenBLAS) vs C++ (OpenMP) |
| `gerar_figuras.py` | gera as imagens usadas na apresentação |
| `compilar.ps1` | compila os `.cpp` (inclui o de `extras/`) |
| `extras/experimento_memoria.py` / `.cpp` | reconstrução com pouca RAM (streaming + float32) |
| `extras/simular_pouca_ram.py` | simula um servidor com pouca RAM (teto real via Job Object) |
