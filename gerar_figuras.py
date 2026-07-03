"""
gerar_figuras.py
===============
Gera TODAS as figuras usadas nos markdowns (APRESENTACAO.md e
EXTRAS_E_GLOSSARIO.md), salvando em imagens/.

  * reconstrucoes de TODOS os sinais (com e sem gabarito), no MESMO tamanho em
    pixels do gabarito (para ficar simetrico no markdown);
  * copia dos gabaritos;
  * curva do ganho gamma;
  * grafico comparativo Python x C++ (le relatorios/throughput.json);
  * grafico "anatomia da iteracao" (overhead).

(A figura do servidor com pouca RAM e' gerada por simular_pouca_ram.py.)
Rode depois de bench_throughput.py (para existir o throughput.json).
"""

import json
import os
import shutil
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import algoritmos as alg

IMG = "imagens"
DATA = "data"
DPI = 100
os.makedirs(IMG, exist_ok=True)

# (sinal, gabarito|None, matriz, largura_px, altura_px, chave, rotulo)
RECONS = [
    ("g-30x30-1.csv", "f-30x30-1.png", "H-2.csv", 1120, 840, "g30_1", "30x30 nº1"),
    ("g-30x30-2.csv", "f-30x30-2.png", "H-2.csv", 1120, 840, "g30_2", "30x30 nº2"),
    ("A-30x30-1.csv", None,            "H-2.csv", 1120, 840, "A30",   "30x30 (sinal A)"),
    ("G-1.csv",       "F-1.png",       "H-1.csv", 560,  420, "G1",    "60x60 nº1"),
    ("G-2.csv",       "F-2.png",       "H-1.csv", 560,  420, "G2",    "60x60 nº2"),
    ("A-60x60-1.csv", None,            "H-1.csv", 560,  420, "A60",   "60x60 (sinal A)"),
]

_cache_H = {}


def _matriz(h_csv):
    if h_csv not in _cache_H:
        _cache_H[h_csv] = alg.carregar_matriz(os.path.join(DATA, h_csv))
    return _cache_H[h_csv]


def salvar_exato(f, caminho_png, titulo, wpx, hpx, algoritmo, inicio, fim, iteracoes):
    """Salva a imagem reconstruida com tamanho EXATO de wpx x hpx pixels, com
    a ficha tecnica exigida (algoritmo, inicio, fim, pixels, iteracoes)
    impressa no rodape da propria figura."""
    lado = int(round(np.sqrt(len(f))))
    pixels = lado * lado
    img = np.abs(f).reshape((lado, lado), order="F")     # ordem Fortran (igual ao gabarito)
    fig = plt.figure(figsize=(wpx / DPI, hpx / DPI), dpi=DPI)
    # margens com mais espaco embaixo para caber a ficha tecnica (tamanho da
    # figura continua EXATO: wpx x hpx, so' a area do eixo fica um pouco menor)
    ax = fig.add_axes([0.10, 0.17, 0.86, 0.75])
    ax.imshow(img, cmap="gray", origin="upper", aspect="equal")
    ax.set_title(titulo)
    passo = max(5, lado // 6)
    ax.set_xticks(np.arange(0, lado + 1, passo))
    ax.set_yticks(np.arange(0, lado + 1, passo))
    ficha = (f"algoritmo={algoritmo} | pixels={pixels} ({lado}x{lado}) | iteracoes={iteracoes}\n"
             f"inicio={inicio} | fim={fim}")
    fig.text(0.5, 0.02, ficha, ha="center", va="bottom", fontsize=6.5, family="monospace")
    fig.savefig(caminho_png, dpi=DPI)                    # SEM bbox_inches -> tamanho exato
    plt.close(fig)


def reconstrucoes():
    """Reconstroi todos os sinais (CGNR) no tamanho do gabarito; copia gabaritos."""
    for sinal, gab, h_csv, w, h, chave, rotulo in RECONS:
        H = _matriz(h_csv)
        g = alg.aplicar_ganho(alg.carregar_sinal(os.path.join(DATA, sinal)))
        inicio = datetime.now().isoformat(timespec="milliseconds")
        f, iters = alg.cgnr(g, H)
        fim = datetime.now().isoformat(timespec="milliseconds")
        salvar_exato(f, os.path.join(IMG, f"rec_{chave}.png"),
                     f"CGNR {rotulo}  ({iters} iter)", w, h,
                     algoritmo="CGNR", inicio=inicio, fim=fim, iteracoes=iters)
        if gab:
            shutil.copy(os.path.join(DATA, gab), os.path.join(IMG, f"gab_{chave}.png"))
        print(f"rec_{chave}.png ({w}x{h})", "+ gabarito" if gab else "(sem gabarito)")
    # um exemplo de CGNE (para a secao do algoritmo), mesmo tamanho
    H = _matriz("H-2.csv")
    g = alg.aplicar_ganho(alg.carregar_sinal(os.path.join(DATA, "g-30x30-1.csv")))
    inicio = datetime.now().isoformat(timespec="milliseconds")
    f, iters = alg.cgne(g, H)
    fim = datetime.now().isoformat(timespec="milliseconds")
    salvar_exato(f, os.path.join(IMG, "rec_cgne_30x30.png"),
                 f"CGNE 30x30 nº1  ({iters} iter)", 1120, 840,
                 algoritmo="CGNE", inicio=inicio, fim=fim, iteracoes=iters)
    print("rec_cgne_30x30.png")


def curva_ganho():
    S = 436
    l = np.arange(1, S + 1)
    gamma = 100 + (1 / 20.0) * l * np.sqrt(l)
    fig, ax = plt.subplots(figsize=(6, 3.2))
    ax.plot(l, gamma, color="#1f77b4")
    ax.set_xlabel("amostra l  (modelo 30×30: S = 436 amostras)")
    ax.set_ylabel("ganho gamma_l")
    ax.set_title("Ganho de sinal:  gamma_l = 100 + (1/20) l sqrt(l)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, "ganho.png"), dpi=110)
    plt.close(fig)
    print("ganho.png")


def grafico_comparacao():
    caminho = "relatorios/throughput.json"
    if not os.path.exists(caminho):
        print("(sem throughput.json - rode bench_throughput.py antes)")
        return
    d = json.load(open(caminho, encoding="utf-8"))
    chaves = [k for k in ("python", "cpp", "cpp_openmp") if k in d]
    rotulos = {"python": "Python\n(NumPy/OpenBLAS)",
               "cpp": "C++\n(OpenBLAS)\nmesma BLAS",
               "cpp_openmp": "C++\n(OpenMP)\nparalelizado"}
    cores = {"python": "#ffb000", "cpp": "#1f77b4", "cpp_openmp": "#2ca02c"}
    labels = [rotulos[k] for k in chaves]
    medios = [d[k]["ms_por_img"] for k in chaves]
    fig, ax = plt.subplots(figsize=(6, 3.8))
    barras = ax.bar(labels, medios, color=[cores[k] for k in chaves])
    ax.set_ylabel("tempo por imagem (ms)")
    ax.set_title("Tempo mediano por imagem — modelo 30×30 (menor = melhor)")
    for b, v in zip(barras, medios):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.0f} ms", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, "comparacao.png"), dpi=110)
    plt.close(fig)
    print("comparacao.png")


def grafico_overhead():
    """Anatomia de uma iteracao: a GEMV (mesma BLAS) domina; a SOBRECARGA (overhead)
    do Python e' o pedacinho onde ele perde tempo. Fatias sao ilustrativas."""
    GEMV = 135.0
    py_sobre = [("alocar arrays novos\n(f = f + alpha*p ...)", 7, "#e69138"),
                ("dispatch do interpretador", 5, "#8e7cc3"),
                ("objetos / coletor de lixo", 3, "#a64d79")]
    cpp_sobre = 5.0
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    ax.barh(1, GEMV, height=0.5, color="#6fa8dc", edgecolor="white")
    x = GEMV
    for nome, larg, cor in py_sobre:
        ax.barh(1, larg, height=0.5, left=x, color=cor, edgecolor="white", label=nome)
        x += larg
    ax.barh(0, GEMV, height=0.5, color="#6fa8dc", edgecolor="white",
            label="GEMV (mesma BLAS) — IGUAL nos dois")
    ax.barh(0, cpp_sobre, height=0.5, left=GEMV, color="#6aa84f", edgecolor="white",
            label="sobrecarga do C++ (mínima, in-place)")
    ax.set_yticks([0, 1]); ax.set_yticklabels(["C++\n(OpenBLAS)", "Python\n(NumPy)"])
    ax.set_xlabel("tempo de uma iteração (ms), modelo 30×30  —  menor = melhor")
    ax.set_title("Onde o tempo vai: a conta pesada é idêntica; a sobrecarga é o que difere")
    ax.text(GEMV / 2, 1, "GEMV", ha="center", va="center", color="white", fontweight="bold")
    ax.text(GEMV / 2, 0, "GEMV", ha="center", va="center", color="white", fontweight="bold")
    ax.set_xlim(0, GEMV + 18)
    ax.set_ylim(-0.6, 1.6)
    # legenda FORA do grafico (abaixo), para nao tampar a barra do C++
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.28), ncol=2,
              fontsize=8, framealpha=0.95)
    fig.savefig(os.path.join(IMG, "overhead.png"), dpi=110, bbox_inches="tight")
    plt.close(fig)
    print("overhead.png")


def grafico_processos_paralelos(ram_mb=256, py_proc=40, cpp_proc=10):
    """Footprint -> paralelismo: quantos processos de reconstrucao cabem na RAM.
    Cada processo Python ocupa ~py_proc MB; cada C++, ~cpp_proc MB. Num servidor
    com ram_mb, cabem muito mais processos C++ em paralelo -> mais throughput."""
    n_py = int(ram_mb // py_proc)
    n_cpp = int(ram_mb // cpp_proc)
    fig, ax = plt.subplots(figsize=(7, 4.4))
    for i in range(n_py):     # pilha de processos Python (caixas grandes)
        ax.bar(0, py_proc, bottom=i * py_proc, width=0.5,
               color="#ffb000", edgecolor="white", linewidth=1.0)
    for i in range(n_cpp):    # pilha de processos C++ (caixas pequenas)
        ax.bar(1, cpp_proc, bottom=i * cpp_proc, width=0.5,
               color="#1f77b4", edgecolor="white", linewidth=0.6)
    ax.axhline(ram_mb, color="#444444", linestyle="--", linewidth=1.3)
    ax.text(-0.55, ram_mb, f"RAM = {ram_mb} MB", va="bottom", ha="left",
            fontsize=9, fontweight="bold", color="#444444")
    ax.text(0, ram_mb * 1.07, f"{n_py} processos\n(~{py_proc} MB cada)",
            ha="center", va="bottom", fontweight="bold", color="#b8860b")
    ax.text(1, ram_mb * 1.07, f"{n_cpp} processos\n(~{cpp_proc} MB cada)",
            ha="center", va="bottom", fontweight="bold", color="#1f77b4")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Python", "C++"])
    ax.set_ylabel("RAM ocupada (MB)")
    ax.set_xlim(-0.6, 1.6); ax.set_ylim(0, ram_mb * 1.30)
    ax.set_title(f"Em {ram_mb} MB de RAM: quantos processos cabem em paralelo?\n"
                 f"(reconstrução por streaming, modelo 60×60)", fontsize=11)
    fig.tight_layout()
    fig.savefig(os.path.join(IMG, "paralelismo.png"), dpi=110)
    plt.close(fig)
    print("paralelismo.png")


def main():
    reconstrucoes()
    curva_ganho()
    grafico_comparacao()
    grafico_overhead()
    grafico_processos_paralelos()
    print("\nfiguras geradas em", IMG)
    print("(a figura do servidor com pouca RAM vem de simular_pouca_ram.py)")


if __name__ == "__main__":
    main()
