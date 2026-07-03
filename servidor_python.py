"""
servidor_python.py
==================
Servidor de reconstrucao - VERSAO INTERPRETADA (Python).

E' a versao do requisito "linguagem interpretada e NAO fortemente tipada".
Carrega a matriz H uma unica vez e fica esperando pedidos do cliente. Para
cada pedido reconstroi a imagem (CGNE ou CGNR) e devolve o resultado.

Protocolo (bem simples, em cima de TCP):
    PEDIDO   ->  linha ASCII  "ALGORITMO TAMANHO\n"  +  TAMANHO doubles (g)
    RESPOSTA <-  linha ASCII  "ALGO|inicio|fim|iteracoes|num_pixels|tempo_ms\n"
                 + num_pixels doubles (imagem f)
              ou, se a rotina de controle de saturacao recusar o pedido:
    RESPOSTA <-  linha ASCII  "SATURADO|motivo\n"   (sem corpo)

Os numeros viajam como float64 binario (rapido e exato, sem texto).
"""

import ctypes
import socket
import time
from datetime import datetime

import numpy as np
import algoritmos as alg

# Comparacao JUSTA: o NumPy roda com a configuracao padrao (livre para usar
# todos os nucleos via BLAS). Nao limitamos nada aqui. O C++ vence porque
# paralelizamos explicitamente os produtos matriz-vetor com OpenMP.

HOST = "127.0.0.1"
PORT = 8101

# A matriz e' escolhida pelo TAMANHO do sinal recebido:
MODELOS = {
    27904: "data/H-2.csv",   # modelo 30x30  (imagem de 900 pixels)
    50816: "data/H-1.csv",   # modelo 60x60  (imagem de 3600 pixels)
}
_cache = {}   # guarda as matrizes ja carregadas (carrega so uma vez)


def obter_matriz(tamanho_g):
    """Devolve a matriz H correspondente ao tamanho do sinal (carrega na 1a vez)."""
    if tamanho_g not in _cache:
        caminho = MODELOS[tamanho_g]
        print(f"[servidor-py] carregando matriz {caminho} ...", flush=True)
        _cache[tamanho_g] = alg.carregar_matriz(caminho)
    return _cache[tamanho_g]


# ----------------------------------------------------------------------
# Rotina de controle de saturacao (Atividade 4 do enunciado):
# mede a RAM disponivel no sistema e recusa novas reconstrucoes quando ela
# esta abaixo de um minimo seguro, em vez de deixar o processo estourar
# memoria (o mesmo cenario testado offline em extras/simular_pouca_ram.py).
# ----------------------------------------------------------------------
class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("sullAvailExtendedVirtual", ctypes.c_uint64),
    ]


RAM_MINIMA_MB = 200   # abaixo disso, recusamos novas reconstrucoes


def ram_disponivel_mb():
    """RAM fisica disponivel agora, via GlobalMemoryStatusEx (Windows)."""
    stat = _MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    return stat.ullAvailPhys / (1024 * 1024)


# --- funcoes auxiliares de rede (ler exatamente N bytes / ler uma linha) ---
def receber_n(conn, n):
    dados = bytearray()
    while len(dados) < n:
        pacote = conn.recv(n - len(dados))
        if not pacote:
            raise ConnectionError("conexao fechada cedo demais")
        dados.extend(pacote)
    return bytes(dados)


def receber_linha(conn):
    linha = bytearray()
    while True:
        b = conn.recv(1)
        if not b:
            break
        if b == b"\n":
            break
        linha.extend(b)
    return linha.decode("ascii")


def atender(conn):
    # 1) le o cabecalho "ALGORITMO TAMANHO"
    cabecalho_pedido = receber_linha(conn).split()
    if len(cabecalho_pedido) != 2:
        return                       # conexao de teste/vazia (probe): ignora
    algoritmo, tamanho = cabecalho_pedido
    tamanho = int(tamanho)

    # 2) le o sinal g (TAMANHO doubles)
    bruto = receber_n(conn, tamanho * 8)
    g = np.frombuffer(bruto, dtype="<f8").copy()

    # 2.5) rotina de controle de saturacao: recusa o pedido se a RAM livre
    # estiver abaixo do minimo seguro, em vez de arriscar um MemoryError
    livre = ram_disponivel_mb()
    if livre < RAM_MINIMA_MB:
        motivo = f"RAM livre {livre:.0f}MB < minimo {RAM_MINIMA_MB}MB"
        conn.sendall(f"SATURADO|{motivo}\n".encode("ascii"))
        print(f"[servidor-py] SATURADO: {motivo}", flush=True)
        return

    # 3) reconstroi  (anota inicio e fim, exigidos no relatorio)
    H = obter_matriz(tamanho)
    inicio = datetime.now()
    t0 = time.perf_counter()
    f, iteracoes = alg.ALGORITMOS[algoritmo](g, H)
    tempo_ms = (time.perf_counter() - t0) * 1000.0
    fim = datetime.now()

    # 4) responde: cabecalho com metadados + imagem
    cabecalho = "{}|{}|{}|{}|{}|{:.3f}\n".format(
        algoritmo + "_PYTHON",
        inicio.isoformat(timespec="milliseconds"),
        fim.isoformat(timespec="milliseconds"),
        iteracoes,
        f.size,
        tempo_ms,
    )
    conn.sendall(cabecalho.encode("ascii"))
    conn.sendall(f.astype("<f8").tobytes())
    print(f"[servidor-py] {algoritmo} -> {iteracoes} iter, {tempo_ms:.1f} ms", flush=True)


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((HOST, PORT))
        servidor.listen(8)
        print(f"[servidor-py] pronto em {HOST}:{PORT}", flush=True)
        while True:
            conn, _ = servidor.accept()
            with conn:
                try:
                    atender(conn)
                except (ConnectionError, OSError):
                    pass             # conexao de teste/cancelada: ignora
                except Exception as e:
                    print(f"[servidor-py] erro: {e}", flush=True)


if __name__ == "__main__":
    main()
