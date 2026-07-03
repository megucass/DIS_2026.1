"""
algoritmos.py
=============
Coracao do projeto: reconstrucao de imagem de ultrassom.

O problema e':            g = H * f
    g -> sinal medido pelos sensores (vetor conhecido)
    H -> matriz do modelo  (conhecida)
    f -> imagem            (o que queremos descobrir)

Como H nao e' inversivel diretamente (problema mal-condicionado), usamos
metodos iterativos do Gradiente Conjugado: CGNE e CGNR.

Este arquivo contem APENAS matematica pura (NumPy). Nao tem rede, nao tem
servidor: e' a parte que o professor realmente pede. Mantivemos tudo simples
e comentado para ser facil de ler.
"""

import os
import numpy as np


# ----------------------------------------------------------------------
# 1) CARREGAR OS DADOS
# ----------------------------------------------------------------------
def carregar_matriz(caminho_csv):
    """Carrega a matriz H. Usa cache .npy (binario) quando existir, pois ler
    o CSV gigante toda vez seria lento."""
    cache = caminho_csv + ".npy"
    if os.path.exists(cache):
        return np.load(cache)
    H = np.loadtxt(caminho_csv, delimiter=",")
    np.save(cache, H)          # salva o cache para a proxima vez
    return H


def carregar_sinal(caminho_csv):
    """Carrega um vetor de sinal g (uma coluna de numeros)."""
    return np.loadtxt(caminho_csv, delimiter=",")


# ----------------------------------------------------------------------
# 2) GANHO DE SINAL (gamma) - requisito do cliente
# ----------------------------------------------------------------------
#   Para cada amostra l (1..S) e cada sensor c (1..N):
#       gamma_l   = 100 + (1/20) * l * sqrt(l)
#       g[l, c]   = g[l, c] * gamma_l
#
#   E' o "ganho por tempo" (TGC): amostras mais profundas (l maior) sao
#   amplificadas para compensar a atenuacao do som no corpo.
def aplicar_ganho(g, n_sensores=64):
    """Aplica o ganho gamma ao sinal g. O sinal vem 'achatado' em um vetor;
    o reorganizamos em S amostras x N sensores para aplicar gamma por amostra.

    N = 64 sensores neste dataset (27904 = 436*64 e 50816 = 794*64)."""
    if len(g) % n_sensores != 0:              # protege contra modelos com outro N
        raise ValueError(f"sinal de tamanho {len(g)} nao e multiplo de {n_sensores} sensores")
    S = len(g) // n_sensores                 # numero de amostras por sensor
    G = g.reshape((S, n_sensores), order="F")  # S linhas (amostras) x N colunas (sensores)
    l = np.arange(1, S + 1)                   # indices das amostras 1..S
    gamma = 100 + (1.0 / 20.0) * l * np.sqrt(l)
    G = G * gamma[:, None]                    # multiplica cada linha l por gamma_l
    return G.reshape(-1, order="F")           # volta a achatar para vetor


# ----------------------------------------------------------------------
# 3) QUANTIDADES DEFINIDAS NO ENUNCIADO (informativas)
# ----------------------------------------------------------------------
def coeficiente_regularizacao(H, g):
    """lambda = max(abs(H^T * g)) * 0.10  (coeficiente de regularizacao)."""
    return np.max(np.abs(H.T @ g)) * 0.10


def fator_reducao(H, iteracoes=20):
    """c = || H^T * H ||_2  (norma espectral, calculada pelo metodo da potencia).

    E' o maior autovalor de H^T*H; indica o quao 'esticada' a matriz e'."""
    n = H.shape[1]
    v = np.random.default_rng(0).random(n)
    v = v / np.linalg.norm(v)
    for _ in range(iteracoes):
        w = H.T @ (H @ v)          # multiplica por H^T*H sem montar a matriz
        v = w / np.linalg.norm(w)
    return float(v @ (H.T @ (H @ v)))


# ----------------------------------------------------------------------
# 4) ALGORITMO CGNE  (Conjugate Gradient Normal Error)
# ----------------------------------------------------------------------
#   f0 = 0
#   r0 = g - H f0
#   p0 = H^T r0
#   repetir:
#       alpha = (r^T r) / (p^T p)
#       f     = f + alpha p
#       r     = r - alpha (H p)
#       beta  = (r_novo^T r_novo) / (r^T r)
#       p     = H^T r_novo + beta p
#   Para quando |erro| < tol  ou  atingir max_iter.
#
#   NOTA sobre o erro: o enunciado define e = ||r_(i+1)||_2 - ||r_i||_2 (sem
#   modulo). Como a norma do residuo do CG e' nao-crescente, essa diferenca
#   "crua" e' quase sempre <= 0 e o criterio pararia sempre na 1a iteracao,
#   contradizendo o requisito de rodar ate 10 iteracoes. Por isso usamos
#   |e| = abs(||r_(i+1)||_2 - ||r_i||_2): a MAGNITUDE da variacao do residuo
#   entre iteracoes, que e' a leitura que faz o criterio de parada funcionar
#   como descrito (ver APRESENTACAO.md, secao 2).
def cgne(g, H, max_iter=10, tol=1e-4):
    f = np.zeros(H.shape[1])
    r = g - H @ f                  # r0  (espaco do sinal)
    p = H.T @ r                    # p0  (espaco da imagem)
    rtr = r @ r
    norma_r_ant = np.sqrt(rtr)

    iters = 0
    for i in range(max_iter):
        iters = i + 1
        Hp = H @ p
        alpha = rtr / (p @ p)
        f = f + alpha * p
        r = r - alpha * Hp

        rtr_novo = r @ r
        norma_r = np.sqrt(rtr_novo)
        # erro = variacao da norma do residuo entre duas iteracoes
        erro = abs(norma_r - norma_r_ant)
        if erro < tol:
            break
        beta = rtr_novo / rtr
        p = H.T @ r + beta * p
        rtr = rtr_novo
        norma_r_ant = norma_r

    return f, iters


# ----------------------------------------------------------------------
# 5) ALGORITMO CGNR  (Conjugate Gradient Normal Residual) - Saad 2003
# ----------------------------------------------------------------------
#   f0 = 0
#   r0 = g - H f0
#   z0 = H^T r0
#   p0 = z0
#   repetir:
#       w     = H p
#       alpha = ||z||^2 / ||w||^2
#       f     = f + alpha p
#       r     = r - alpha w
#       z_novo= H^T r
#       beta  = ||z_novo||^2 / ||z||^2
#       p     = z_novo + beta p
#   Para quando |erro| < tol  ou  atingir max_iter.
#   (mesma nota do CGNE sobre o modulo em |erro| - ver acima)
def cgnr(g, H, max_iter=10, tol=1e-4):
    f = np.zeros(H.shape[1])
    r = g - H @ f                  # r0  (espaco do sinal)
    z = H.T @ r                    # z0  (espaco da imagem)
    p = z.copy()
    ztz = z @ z
    norma_r_ant = np.linalg.norm(r)

    iters = 0
    for i in range(max_iter):
        iters = i + 1
        w = H @ p
        alpha = ztz / (w @ w)
        f = f + alpha * p
        r = r - alpha * w

        norma_r = np.linalg.norm(r)
        erro = abs(norma_r - norma_r_ant)
        if erro < tol:
            break
        z = H.T @ r
        ztz_novo = z @ z
        beta = ztz_novo / ztz
        p = z + beta * p
        ztz = ztz_novo
        norma_r_ant = norma_r

    return f, iters


# tabela para escolher o algoritmo pelo nome
ALGORITMOS = {"CGNE": cgne, "CGNR": cgnr}


# ----------------------------------------------------------------------
# 6) SALVAR A IMAGEM RECONSTRUIDA  (PNG em tons de cinza)
# ----------------------------------------------------------------------
# O enunciado exige que CADA IMAGEM contenha, no minimo: identificacao do
# algoritmo, data/hora de inicio, data/hora de fim, tamanho em pixels e o
# numero de iteracoes executadas. Por isso essa "ficha tecnica" e' impressa
# dentro do proprio PNG (nao so' no relatorio em markdown).
def salvar_imagem(f, caminho_png, algoritmo, inicio, fim, iteracoes, titulo=None):
    """Transforma o vetor f em uma imagem quadrada e salva como PNG, com a
    ficha tecnica (algoritmo, inicio, fim, pixels, iteracoes) impressa
    junto com a figura."""
    import matplotlib
    matplotlib.use("Agg")                 # backend sem janela (so salva arquivo)
    import matplotlib.pyplot as plt

    lado = int(round(np.sqrt(len(f))))    # 900 -> 30 ; 3600 -> 60
    pixels = lado * lado
    # reshape em ordem "F" (coluna a coluna) para casar com a orientacao da
    # imagem de referencia, que foi gerada no MATLAB (column-major).
    img = np.abs(f).reshape((lado, lado), order="F")  # valor absoluto, como na referencia

    fig, ax = plt.subplots(figsize=(5, 5.6))
    ax.imshow(img, cmap="gray", origin="upper")
    ax.set_title(titulo or algoritmo)
    ax.set_xticks(np.arange(0, lado + 1, 5))
    ax.set_yticks(np.arange(0, lado + 1, 5))

    ficha = (f"algoritmo={algoritmo}  |  pixels={pixels} ({lado}x{lado})  |  iteracoes={iteracoes}\n"
             f"inicio={inicio}  |  fim={fim}")
    fig.text(0.5, 0.01, ficha, ha="center", va="bottom", fontsize=7, family="monospace")

    os.makedirs(os.path.dirname(caminho_png) or ".", exist_ok=True)
    fig.subplots_adjust(bottom=0.18)
    fig.savefig(caminho_png, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return caminho_png
