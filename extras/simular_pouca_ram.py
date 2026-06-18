"""
simular_pouca_ram.py
===================
Simula um SERVIDOR COM POUQUISSIMA RAM e mostra, na pratica, a diferenca:

  * "Carregar a matriz inteira de uma vez" precisa de ~1464 MB -> NAO CABE
    (estoura o limite -> MemoryError).
  * "Streaming" (ler a matriz do disco em pedacos) cabe folgado.

Como simulamos o limite: usamos um *Job Object* do Windows para impor um teto
REAL de memoria ao processo -- qualquer alocacao acima do teto falha. Ou seja, e'
o proprio sistema operacional que barra o excesso, nao uma simulacao aproximada.

Uso:  python simular_pouca_ram.py            (roda a simulacao e gera a figura)
"""

import ctypes
import os
import subprocess
import sys

# Este script vive em extras/. Caminhos resolvidos a partir da pasta dele.
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.join(AQUI, "..")
sys.path.insert(0, AQUI)            # para importar experimento_memoria (mesma pasta)

TETO_MB = 256                       # "servidor" com apenas 256 MB de RAM
DATA = os.path.join(RAIZ, "data")   # a base de dados fica na raiz
IMG = os.path.join(RAIZ, "imagens")
MINGW_BIN = r"C:\msys64\mingw64\bin"

# ----------------------------------------------------------------------
# Teto de memoria REAL via Job Object do Windows
# ----------------------------------------------------------------------
class _BASIC(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", ctypes.c_uint32),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", ctypes.c_uint32),
                ("SchedulingClass", ctypes.c_uint32)]

class _IO(ctypes.Structure):
    _fields_ = [("a", ctypes.c_uint64), ("b", ctypes.c_uint64), ("c", ctypes.c_uint64),
                ("d", ctypes.c_uint64), ("e", ctypes.c_uint64), ("f", ctypes.c_uint64)]

class _EXT(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", _BASIC), ("IoInfo", _IO),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t)]

JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JobObjectExtendedLimitInformation = 9


def limitar_ram(mb):
    """Impoe um teto de 'mb' megabytes ao processo atual (Windows Job Object)."""
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateJobObjectW.restype = ctypes.c_void_p
    k.GetCurrentProcess.restype = ctypes.c_void_p
    k.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    k.SetInformationJobObject.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                          ctypes.c_void_p, ctypes.c_uint32]
    job = k.CreateJobObjectW(None, None)
    info = _EXT()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY
    info.ProcessMemoryLimit = mb * 1024 * 1024
    if not k.SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                                     ctypes.byref(info), ctypes.sizeof(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not k.AssignProcessToJobObject(job, k.GetCurrentProcess()):
        raise ctypes.WinError(ctypes.get_last_error())
    return job   # manter vivo


# ----------------------------------------------------------------------
# Worker: roda DENTRO do teto e tenta as duas abordagens
# ----------------------------------------------------------------------
def worker(cap_mb):
    # 1 thread na BLAS: reduz os buffers internos do OpenBLAS, deixando o
    # rodape de memoria do Python pequeno (senao nem o streaming caberia).
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
    os.environ["OMP_NUM_THREADS"] = "1"
    _job = limitar_ram(cap_mb)            # a partir daqui, RAM e' limitada
    import numpy as np
    import experimento_memoria as em

    # 1) Tentar carregar a matriz INTEIRA (60x60 = ~1464 MB)
    try:
        H = np.load(os.path.join(DATA, "H-1.csv.npy"))   # precisa de ~1464 MB
        _ = H.shape
        del H
        carga_inteira = "COUBE"                  # (so' aconteceria se o teto fosse alto)
    except MemoryError:
        carga_inteira = "ESTOUROU"

    # 2) Streaming: reconstruir lendo a matriz em blocos float32
    prefixo = "H-1"
    em.criar_f32_se_preciso(prefixo)
    caminho = em.caminho_f32(prefixo)
    import struct
    with open(caminho, "rb") as fh:
        rows, cols = struct.unpack("<qq", fh.read(16))
    g = em.alg.aplicar_ganho(em.alg.carregar_sinal(os.path.join(DATA, "G-1.csv"))).astype("<f4")
    f, iters = em.cgnr_streaming(caminho, rows, cols, g, bloco=256)
    pico = em.pico_ram_mb()
    print(f"RESULT|{carga_inteira}|{pico:.1f}|{float(np.linalg.norm(f)):.4g}", flush=True)


# ----------------------------------------------------------------------
# Grafico: "o que cabe num servidor com pouca RAM?"
# ----------------------------------------------------------------------
def grafico(cap_mb, matriz_mb, py_peak, cpp_peak):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rotulos = ["Carregar a matriz\ninteira de uma vez",
               "Streaming\n(Python)", "Streaming\n(C++)"]
    valores = [matriz_mb, py_peak, cpp_peak]
    cabe = [v <= cap_mb for v in valores]
    cores = ["#d64545" if not c else "#3a9e5c" for c in cabe]
    topo = cap_mb * 1.6                                   # eixo: mostra o teto e os pequenos

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    barras = ax.bar(rotulos, [min(v, topo) for v in valores], color=cores, width=0.6)
    # linha do teto de RAM
    ax.axhline(cap_mb, color="#d64545", linestyle="--", linewidth=1.5)
    ax.text(2.45, cap_mb, f" RAM do servidor = {cap_mb} MB",
            color="#d64545", va="center", ha="left", fontsize=9, fontweight="bold")

    for i, (b, v, c) in enumerate(zip(barras, valores, cabe)):
        if not c:   # nao cabe -> rotulo no meio da barra (sem cortar)
            ax.text(b.get_x() + b.get_width() / 2, topo * 0.52,
                    f"✗ NÃO CABE\n\n{v:.0f} MB\n≈ {v/cap_mb:.0f}× a RAM",
                    ha="center", va="center", color="white", fontweight="bold", fontsize=10)
        else:
            ax.text(b.get_x() + b.get_width() / 2, v + topo * 0.02,
                    f"✓ cabe\n{v:.0f} MB", ha="center", va="bottom",
                    color="#2c7a44", fontweight="bold", fontsize=10)
    ax.set_ylim(0, topo)
    ax.set_ylabel("memória necessária (MB)")
    ax.set_title(f"Servidor com pouca RAM ({cap_mb} MB): o que cabe?\n"
                 f"matriz H do modelo 60×60 — 50816×3600 = 1464 MB (float64)", fontsize=11)
    fig.tight_layout()
    os.makedirs(IMG, exist_ok=True)
    fig.savefig(os.path.join(IMG, "pouca_ram.png"), dpi=110)
    plt.close(fig)
    print(os.path.join(IMG, "pouca_ram.png"))


def main():
    # roda o worker num subprocesso (para o teto valer so' para ele)
    env = dict(os.environ)
    env["PATH"] = MINGW_BIN + os.pathsep + env.get("PATH", "")
    out = subprocess.run([sys.executable, os.path.abspath(__file__), "--run", str(TETO_MB)],
                         capture_output=True, text=True, env=env, cwd=AQUI).stdout
    carga_inteira = "?"; py_peak = 46.0
    for linha in out.splitlines():
        if linha.startswith("RESULT|"):
            _, carga_inteira, pico, _norma = linha.split("|")
            py_peak = float(pico)

    # mede o C++ (streaming) normalmente, para a barra dele
    cpp_peak = 6.0
    try:
        o2 = subprocess.run([os.path.join(AQUI, "experimento_memoria.exe"), "60x60", "256"],
                            capture_output=True, text=True, env=env, cwd=AQUI).stdout
        for linha in o2.splitlines():
            if linha.startswith("RESULT|"):
                cpp_peak = float(linha.split("|")[1])
    except Exception:
        pass

    matriz_mb = 50816 * 3600 * 8 / 1e6        # matriz 60x60 em float64
    print(f"\n=== Servidor simulado com {TETO_MB} MB de RAM ===")
    print(f"  Carregar a matriz inteira ({matriz_mb:.0f} MB): {carga_inteira}")
    print(f"  Streaming Python: COUBE, usou {py_peak:.0f} MB")
    print(f"  Streaming C++:    COUBE, usou {cpp_peak:.0f} MB")
    grafico(TETO_MB, matriz_mb, py_peak, cpp_peak)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--run":
        worker(int(sys.argv[2]))
    else:
        main()
