"""
experimento_memoria.py
=====================
EXPERIMENTO SEPARADO: reconstrucao com MUITO POUCA memoria RAM.

Ideia: em vez de carregar a matriz H inteira (1,46 GB no modelo 60x60!), nos a
lemos do disco EM BLOCOS e em precisao float32 (metade do tamanho). Assim o
programa nunca segura a matriz toda -- o pico de RAM fica minusculo, do tamanho
de UM bloco. Isso "força criatividade no codigo" e mostra onde a linguagem
compilada leva vantagem: controle fino de memoria.

Este arquivo tem dois modos:
  * worker  (--run --modelo 30x30|60x60): roda a reconstrucao por streaming e
            imprime o pico de RAM e o tempo. NAO importa matplotlib, para o
            footprint medido ser honesto.
  * orquestrador (sem argumentos): garante os arquivos float32, roda o worker
            Python e o worker C++ (experimento_memoria.exe) para os dois modelos,
            mede o pico de RAM de cada um e gera o grafico imagens/memoria.png.

Uso:  python experimento_memoria.py
"""

import argparse
import ctypes
import os
import struct
import subprocess
import sys
import time

# Este script vive em extras/. Resolvemos os caminhos a partir da pasta dele,
# para funcionar independentemente de onde for chamado.
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(AQUI, "..")
sys.path.insert(0, RAIZ)           # para achar algoritmos.py (na raiz do projeto)

import numpy as np
import algoritmos as alg           # leve: importa so numpy (matplotlib e' lazy la dentro)

DATA = os.path.join(RAIZ, "data")  # a base de dados fica na raiz
IMG = os.path.join(RAIZ, "imagens")
MODELOS = {"30x30": ("H-2", "g-30x30-1.csv"),
           "60x60": ("H-1", "G-1.csv")}
BLOCO = 512                        # quantas linhas de H lemos por vez
MINGW_BIN = r"C:\msys64\mingw64\bin"


# ----------------------------------------------------------------------
# Pico de memoria do processo (WinAPI via ctypes - sem instalar nada)
# ----------------------------------------------------------------------
class _PMC(ctypes.Structure):
    _fields_ = [("cb", ctypes.c_uint32), ("PageFaultCount", ctypes.c_uint32),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def pico_ram_mb():
    k32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    # tipos explicitos: senao o handle de 64 bits e' truncado e a chamada falha
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(_PMC), ctypes.c_uint32]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    c = _PMC()
    c.cb = ctypes.sizeof(c)
    psapi.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb)
    return c.PeakWorkingSetSize / 1e6


# ----------------------------------------------------------------------
# Cria o arquivo float32 (uma vez), convertendo o .bin float64 EM BLOCOS
# ----------------------------------------------------------------------
def caminho_f32(prefixo):
    return os.path.join(DATA, prefixo + ".f32.bin")


def criar_f32_se_preciso(prefixo):
    dst = caminho_f32(prefixo)
    if os.path.exists(dst):
        return dst
    src = os.path.join(DATA, prefixo + ".bin")            # float64 (do preparar_dados.py)
    print(f"[mem] criando {dst} (float32, em blocos) ...", flush=True)
    with open(src, "rb") as s, open(dst, "wb") as d:
        rows, cols = struct.unpack("<qq", s.read(16))
        d.write(struct.pack("<qq", rows, cols))
        i = 0
        while i < rows:
            b = min(BLOCO, rows - i)
            blk = np.fromfile(s, dtype="<f8", count=b * cols).astype("<f4")
            blk.tofile(d)
            i += b
    return dst


# ----------------------------------------------------------------------
# Produtos matriz-vetor LENDO H DO DISCO EM BLOCOS (pico de RAM = 1 bloco)
# ----------------------------------------------------------------------
def mat_stream(path, m, n, p, bloco):
    """w = H * p, lendo H em blocos de 'bloco' linhas."""
    w = np.empty(m, dtype=np.float32)
    with open(path, "rb") as fh:
        fh.seek(16)
        i = 0
        while i < m:
            b = min(bloco, m - i)
            blk = np.fromfile(fh, dtype="<f4", count=b * n).reshape(b, n)
            w[i:i + b] = blk @ p
            i += b
    return w


def matT_stream(path, m, n, r, bloco):
    """z = H^T * r, lendo H em blocos de 'bloco' linhas e acumulando."""
    z = np.zeros(n, dtype=np.float32)
    with open(path, "rb") as fh:
        fh.seek(16)
        i = 0
        while i < m:
            b = min(bloco, m - i)
            blk = np.fromfile(fh, dtype="<f4", count=b * n).reshape(b, n)
            z += blk.T @ r[i:i + b]
            i += b
    return z


def cgnr_streaming(path, m, n, g, bloco, max_iter=10, tol=1e-4):
    f = np.zeros(n, dtype=np.float32)
    r = g.copy()
    z = matT_stream(path, m, n, r, bloco)
    p = z.copy()
    ztz = float(z @ z)
    norma_r_ant = float(np.linalg.norm(r))
    iters = 0
    for k in range(max_iter):
        iters = k + 1
        w = mat_stream(path, m, n, p, bloco)
        alpha = np.float32(ztz / float(w @ w))
        f += alpha * p          # in-place (sem alocar novo)
        r -= alpha * w          # in-place
        norma_r = float(np.linalg.norm(r))
        if abs(norma_r - norma_r_ant) < tol:
            break
        z = matT_stream(path, m, n, r, bloco)
        ztz_novo = float(z @ z)
        beta = np.float32(ztz_novo / ztz)
        p = z + beta * p
        ztz, norma_r_ant = ztz_novo, norma_r
    return f, iters


# ----------------------------------------------------------------------
# Worker: roda a reconstrucao por streaming e reporta pico de RAM + tempo
# ----------------------------------------------------------------------
def worker(modelo, bloco):
    prefixo, sinal = MODELOS[modelo]
    path = caminho_f32(prefixo)
    with open(path, "rb") as fh:
        rows, cols = struct.unpack("<qq", fh.read(16))
    g = alg.aplicar_ganho(alg.carregar_sinal(os.path.join(DATA, sinal))).astype("<f4")
    t0 = time.perf_counter()
    f, iters = cgnr_streaming(path, rows, cols, g, bloco)
    dt = (time.perf_counter() - t0) * 1000.0
    # linha parseavel: RESULT|pico_mb|tempo_ms|norma|iters
    print(f"RESULT|{pico_ram_mb():.1f}|{dt:.1f}|{float(np.linalg.norm(f)):.4g}|{iters}", flush=True)


# ----------------------------------------------------------------------
# Orquestrador: SERIE de tetos cada vez mais agressivos (bloco menor = menos RAM)
# ----------------------------------------------------------------------
# do moderado ao EXTREMO (1 = uma linha por vez)
BLOCOS_SERIE = [1024, 256, 64, 16, 4, 1]
MODELO_SERIE = "60x60"          # modelo onde a memoria realmente aperta
TIMEOUT_S = 180                 # se um teto extremo demorar demais, marca como N/A


def _rodar(cmd, env=None):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, env=env,
                             cwd=AQUI, timeout=TIMEOUT_S).stdout   # cwd=extras (exe le ../data)
    except subprocess.TimeoutExpired:
        return None
    for linha in out.splitlines():
        if linha.startswith("RESULT|"):
            _, pico, tempo, norma, iters = linha.split("|")
            return {"pico_mb": float(pico), "tempo_ms": float(tempo),
                    "norma": float(norma), "iters": int(iters)}
    return None


def grafico_serie(modelo, full_mb, blocos, pts_py, pts_cpp):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    # pega so os pontos que rodaram (nao None)
    bp = [(b, p, c) for b, p, c in zip(blocos, pts_py, pts_cpp) if p and c]
    bs = [b for b, _, _ in bp]
    fig, (axm, axt) = plt.subplots(1, 2, figsize=(10, 3.8))

    axm.plot(bs, [p["pico_mb"] for _, p, _ in bp], "o-", color="#ffb000", label="Python")
    axm.plot(bs, [c["pico_mb"] for _, _, c in bp], "s-", color="#1f77b4", label="C++")
    axm.set_xscale("log", base=2); axm.invert_xaxis()
    axm.set_xlabel("tamanho do bloco (linhas)  ←  mais agressivo")
    axm.set_ylabel("pico de RAM (MB)")
    axm.set_title(f"RAM x teto — modelo {modelo} (matriz H 50816×3600 = {full_mb:.0f} MB)")
    axm.grid(alpha=0.3); axm.legend()

    axt.plot(bs, [p["tempo_ms"] / 1000 for _, p, _ in bp], "o-", color="#ffb000", label="Python")
    axt.plot(bs, [c["tempo_ms"] / 1000 for _, _, c in bp], "s-", color="#1f77b4", label="C++")
    axt.set_xscale("log", base=2); axt.invert_xaxis()
    axt.set_xlabel("tamanho do bloco (linhas)  ←  mais agressivo")
    axt.set_ylabel("tempo (s)")
    axt.set_title("Custo: quanto menor o teto, mais lento")
    axt.grid(alpha=0.3); axt.legend()

    fig.tight_layout()
    os.makedirs(IMG, exist_ok=True)
    fig.savefig(os.path.join(IMG, "memoria_serie.png"), dpi=110)
    plt.close(fig)
    print(os.path.join(IMG, "memoria_serie.png"))


def orquestrar():
    prefixo = MODELOS[MODELO_SERIE][0]
    criar_f32_se_preciso(prefixo)
    with open(caminho_f32(prefixo), "rb") as fh:
        rows, cols = struct.unpack("<qq", fh.read(16))
    full_mb = rows * cols * 8 / 1e6
    env = dict(os.environ)
    env["PATH"] = MINGW_BIN + os.pathsep + env.get("PATH", "")

    print(f"=== SERIE de tetos de memoria  (modelo {MODELO_SERIE}, "
          f"H inteira em float64 = {full_mb:.0f} MB) ===")
    print(f"{'bloco':>6} | {'Python RAM':>11} {'tempo':>8} | {'C++ RAM':>9} {'tempo':>8} | RAM C++/Py")
    print("-" * 66)
    pts_py, pts_cpp = [], []
    for bloco in BLOCOS_SERIE:
        py = _rodar([sys.executable, os.path.abspath(__file__),
                     "--run", "--modelo", MODELO_SERIE, "--bloco", str(bloco)], env)
        cpp = _rodar([os.path.join(AQUI, "experimento_memoria.exe"), MODELO_SERIE, str(bloco)], env)
        pts_py.append(py); pts_cpp.append(cpp)
        extra = "  <- EXTREMO (1 linha por vez)" if bloco == 1 else ""
        if py and cpp:
            print(f"{bloco:>6} | {py['pico_mb']:8.1f} MB {py['tempo_ms']/1000:6.1f}s | "
                  f"{cpp['pico_mb']:6.1f} MB {cpp['tempo_ms']/1000:6.1f}s | "
                  f"{py['pico_mb']/cpp['pico_mb']:5.1f}x{extra}")
        else:
            print(f"{bloco:>6} | (N/A: passou de {TIMEOUT_S}s){extra}")
    grafico_serie(MODELO_SERIE, full_mb, BLOCOS_SERIE, pts_py, pts_cpp)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true", help="modo worker (interno)")
    ap.add_argument("--modelo", choices=list(MODELOS), default="30x30")
    ap.add_argument("--bloco", type=int, default=512)
    args = ap.parse_args()
    if args.run:
        worker(args.modelo, args.bloco)
    else:
        orquestrar()


if __name__ == "__main__":
    main()
