"""
cliente.py
=========
Cliente da reconstrucao de imagem.

O que ele faz (requisitos do "Cliente" no enunciado):
  * monta UMA sequencia de sinais (g) e a envia em intervalos de tempo
    aleatorios;
  * o ganho do sinal e o modelo da imagem (30x30 ou 60x60) sao sorteados
    aleatoriamente;
  * CADA sinal da sequencia e' reconstruido pelas DUAS versoes de algoritmo
    (CGNE e CGNR) - "a sequencia de sinais enviados deve ser a mesma para
    as duas versoes de algoritmos de reconstrucao";
  * a MESMA sequencia (sinais + ganho + algoritmos) e' usada para o servidor
    Python e para o C++ (seed fixa), para a comparacao ser justa;
  * gera um relatorio com TODAS as imagens reconstruidas (com link para o
    PNG), n. de iteracoes e tempo de reconstrucao;
  * se o servidor responder "saturado" (poucos recursos), tenta de novo com
    espera antes de desistir daquela reconstrucao;
  * no final, compara as duas versoes (Python x C++).

Uso:
    python cliente.py                 # sobe os dois servidores e compara
    python cliente.py --servidor python
    python cliente.py --n 8           # 8 sinais na sequencia
"""

import argparse
import json
import os
import random
import socket
import subprocess
import sys
import time
from datetime import datetime

import numpy as np
import algoritmos as alg

HOST = "127.0.0.1"
PORTAS = {"python": 8101, "cpp": 8102, "cpp_openmp": 8103}
EXES = {"cpp": "servidor_cpp.exe", "cpp_openmp": "servidor_cpp_openmp.exe"}
MINGW_BIN = r"C:\msys64\mingw64\bin"   # DLLs da OpenBLAS / runtime do MinGW

# Sinais disponiveis - os dois modelos (30x30 e 60x60), para que "o modelo da
# imagem" sorteado pelo cliente varie de verdade entre os dois tamanhos.
SINAIS = ["g-30x30-1.csv", "g-30x30-2.csv", "A-30x30-1.csv",
          "G-1.csv", "G-2.csv", "A-60x60-1.csv"]
ALGORITMOS_CLIENTE = ["CGNE", "CGNR"]
SEED = 42


# ----------------------------------------------------------------------
# Geracao da sequencia de trabalhos (IGUAL para os dois servidores)
# ----------------------------------------------------------------------
def montar_sequencia(n):
    """Sorteia n sinais (com ganho e intervalo aleatorios). Cada sinal e'
    reconstruido pelas DUAS versoes de algoritmo (CGNE e CGNR) em rodar(),
    entao a mesma sequencia de sinais (g) acaba sendo usada para as duas
    versoes de algoritmos de reconstrucao, como pede o enunciado."""
    rnd = random.Random(SEED)
    seq = []
    for _ in range(n):
        seq.append({
            "sinal": rnd.choice(SINAIS),
            "ganho": rnd.choice([True, False]),
            "intervalo": rnd.uniform(0.05, 0.30),   # intervalo de tempo aleatorio
        })
    return seq


# ----------------------------------------------------------------------
# Comunicacao com o servidor
# ----------------------------------------------------------------------
class ServidorSaturado(Exception):
    """O servidor recusou o pedido porque a rotina de controle de saturacao
    (RAM disponivel abaixo do minimo seguro) barrou a reconstrucao."""


def _receber_linha(s):
    linha = bytearray()
    while True:
        b = s.recv(1)
        if not b or b == b"\n":
            break
        linha.extend(b)
    return linha.decode("ascii")


def _receber_n(s, n):
    dados = bytearray()
    while len(dados) < n:
        pacote = s.recv(n - len(dados))
        if not pacote:
            raise ConnectionError("conexao fechada")
        dados.extend(pacote)
    return bytes(dados)


def reconstruir(porta, algoritmo, g):
    """Envia g para o servidor e recebe (metadados, imagem f).

    Se o servidor estiver com poucos recursos, a rotina de controle de
    saturacao dele responde "SATURADO|motivo" (sem corpo/imagem); nesse
    caso levantamos ServidorSaturado para o chamador decidir se tenta de
    novo."""
    t0 = time.perf_counter()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, porta))
        s.sendall(f"{algoritmo} {g.size}\n".encode("ascii"))
        s.sendall(g.astype("<f8").tobytes())
        cab = _receber_linha(s).split("|")
        if cab[0] == "SATURADO":
            raise ServidorSaturado(cab[1] if len(cab) > 1 else "recursos insuficientes")
        npix = int(cab[4])
        f = np.frombuffer(_receber_n(s, npix * 8), dtype="<f8").copy()
    latencia_ms = (time.perf_counter() - t0) * 1000.0
    meta = {
        "algoritmo": cab[0], "inicio": cab[1], "fim": cab[2],
        "iteracoes": int(cab[3]), "pixels": npix,
        "tempo_solver_ms": float(cab[5]), "latencia_ms": latencia_ms,
    }
    return meta, f


def reconstruir_com_retentativa(porta, algoritmo, g, tentativas=3, espera=0.5):
    """Chama reconstruir(); se o servidor estiver saturado, espera um pouco
    e tenta de novo (em vez de simplesmente desistir) - e' a parte do
    cliente que reage a rotina de controle de saturacao do servidor."""
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            return reconstruir(porta, algoritmo, g)
        except ServidorSaturado as e:
            ultimo_erro = e
            print(f"      servidor saturado ({e}); nova tentativa em {espera:.1f}s "
                  f"[{tentativa}/{tentativas}]")
            time.sleep(espera)
    raise ServidorSaturado(f"continuou saturado apos {tentativas} tentativas ({ultimo_erro})")


# ----------------------------------------------------------------------
# Subir / derrubar os servidores
# ----------------------------------------------------------------------
def iniciar_servidor(tipo):
    if tipo == "python":
        proc = subprocess.Popen([sys.executable, "servidor_python.py"])
    else:
        env = dict(os.environ)
        env["PATH"] = MINGW_BIN + os.pathsep + env.get("PATH", "")
        exe = os.path.abspath(EXES[tipo])   # caminho explicito (Windows nao busca no cwd)
        proc = subprocess.Popen([exe], env=env)
    # espera a porta abrir
    porta = PORTAS[tipo]
    for _ in range(120):
        try:
            with socket.socket() as s:
                s.settimeout(0.5)
                s.connect((HOST, porta))
            return proc
        except OSError:
            time.sleep(0.25)
    proc.terminate()
    raise RuntimeError(f"servidor {tipo} nao subiu")


def parar_servidor(proc):
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


# ----------------------------------------------------------------------
# Rodar a sequencia inteira contra um servidor
# ----------------------------------------------------------------------
def rodar(tipo, sequencia, dir_imagens):
    porta = PORTAS[tipo]
    print(f"\n=== Servidor {tipo.upper()} (porta {porta}) ===")
    proc = iniciar_servidor(tipo)
    resultados = []
    try:
        t_total = time.perf_counter()
        for i, job in enumerate(sequencia, start=1):
            time.sleep(job["intervalo"])                 # intervalo aleatorio
            g = alg.carregar_sinal(os.path.join("data", job["sinal"]))
            if job["ganho"]:
                g = alg.aplicar_ganho(g)

            # o MESMO sinal (g) e' reconstruido pelas duas versoes de
            # algoritmo (CGNE e CGNR) - requisito 4 do Cliente
            for algoritmo in ALGORITMOS_CLIENTE:
                try:
                    meta, f = reconstruir_com_retentativa(porta, algoritmo, g)
                except ServidorSaturado as e:
                    print(f"  [{i:02d}] {job['sinal']:<16} {algoritmo:<5} FALHOU: {e}")
                    resultados.append({
                        "idx": i, "sinal": job["sinal"], "ganho": job["ganho"],
                        "algoritmo": algoritmo, "falhou": True, "motivo": str(e),
                        "iteracoes": 0, "pixels": 0, "inicio": "-", "fim": "-",
                        "tempo_solver_ms": 0.0, "imagem": None,
                    })
                    continue

                nome_img = f"{tipo}_{i:02d}_{algoritmo}.png"
                titulo = f"{meta['algoritmo']}  |  {meta['iteracoes']} iter  |  {meta['tempo_solver_ms']:.1f} ms"
                alg.salvar_imagem(f, os.path.join(dir_imagens, nome_img),
                                   algoritmo=meta["algoritmo"], inicio=meta["inicio"],
                                   fim=meta["fim"], iteracoes=meta["iteracoes"], titulo=titulo)

                meta.update({"idx": i, "sinal": job["sinal"], "ganho": job["ganho"],
                             "falhou": False, "imagem": nome_img})
                resultados.append(meta)
                print(f"  [{i:02d}] {job['sinal']:<16} {meta['algoritmo']:<11} "
                      f"ganho={'sim' if job['ganho'] else 'nao':<3} "
                      f"iter={meta['iteracoes']:<2} solver={meta['tempo_solver_ms']:6.1f} ms")
        tempo_total = time.perf_counter() - t_total
    finally:
        parar_servidor(proc)

    # metricas de tempo so' contam as reconstrucoes que deram certo
    # (as saturadas/falhadas nao tem tempo de solver real)
    solver = [r["tempo_solver_ms"] for r in resultados if not r.get("falhou")]
    n_falhas = sum(1 for r in resultados if r.get("falhou"))
    resumo = {
        "tipo": tipo,
        "n": len(resultados),
        "n_falhas": n_falhas,
        "tempo_total_s": tempo_total,
        "tempo_solver_total_ms": sum(solver),
        "tempo_solver_medio_ms": sum(solver) / len(solver) if solver else 0,
        "throughput_img_s": len(solver) / (sum(solver) / 1000.0) if solver else 0,
        "resultados": resultados,
    }
    print(f"  -> total {tempo_total:.2f}s | solver soma {resumo['tempo_solver_total_ms']:.1f} ms "
          f"| medio {resumo['tempo_solver_medio_ms']:.1f} ms"
          + (f" | {n_falhas} falha(s)" if n_falhas else ""))
    return resumo


# ----------------------------------------------------------------------
# Relatorio em markdown
# ----------------------------------------------------------------------
def escrever_relatorio(resumos, sequencia, caminho_md):
    os.makedirs(os.path.dirname(caminho_md), exist_ok=True)
    L = []
    L.append("# Relatorio de Reconstrucao\n")
    L.append(f"Gerado em {datetime.now().isoformat(timespec='seconds')} | "
             f"{len(sequencia)} sinais por servidor (mesma sequencia).\n")

    for r in resumos:
        L.append(f"\n## Servidor {r['tipo'].upper()}\n")
        L.append("| # | sinal | algoritmo | ganho | pixels | iter | inicio | fim | solver (ms) | imagem |")
        L.append("|--:|-------|-----------|:-----:|-------:|:----:|--------|-----|------------:|--------|")
        for x in r["resultados"]:
            if x.get("falhou"):
                L.append(f"| {x['idx']} | {x['sinal']} | {x['algoritmo']} | "
                         f"{'sim' if x['ganho'] else 'nao'} | - | - | - | - | - | "
                         f"**FALHOU** ({x.get('motivo', 'saturado')}) |")
                continue
            imagem_md = f"[{x['imagem']}](imagens/{x['imagem']})" if x.get("imagem") else "-"
            L.append(f"| {x['idx']} | {x['sinal']} | {x['algoritmo']} | "
                     f"{'sim' if x['ganho'] else 'nao'} | {x['pixels']} | {x['iteracoes']} | "
                     f"{x['inicio'].split('T')[1]} | {x['fim'].split('T')[1]} | "
                     f"{x['tempo_solver_ms']:.1f} | {imagem_md} |")
        L.append(f"\n**Soma solver:** {r['tempo_solver_total_ms']:.1f} ms | "
                 f"**Medio:** {r['tempo_solver_medio_ms']:.1f} ms | "
                 f"**Throughput:** {r['throughput_img_s']:.1f} img/s"
                 + (f" | **Falhas (saturacao):** {r['n_falhas']}" if r.get("n_falhas") else "")
                 + "\n")

    # comparacao
    if len(resumos) == 2:
        a, b = resumos  # python, cpp
        L.append("\n## Comparacao Python x C++\n")
        L.append("| metrica | Python | C++ | mais rapido |")
        L.append("|---------|-------:|----:|:-----------:|")
        py, cpp = a["tempo_solver_medio_ms"], b["tempo_solver_medio_ms"]
        L.append(f"| solver medio (ms) | {py:.1f} | {cpp:.1f} | "
                 f"{'C++' if cpp < py else 'Python'} |")
        L.append(f"| throughput (img/s) | {a['throughput_img_s']:.1f} | {b['throughput_img_s']:.1f} | "
                 f"{'C++' if b['throughput_img_s'] > a['throughput_img_s'] else 'Python'} |")
        if py <= cpp:
            L.append(f"\n**Python foi {cpp / py:.2f}x mais rapido que o C++ neste teste.**\n")
        else:
            L.append(f"\n**C++ foi {py / cpp:.2f}x mais rapido que o Python neste teste.**\n")

    with open(caminho_md, "w", encoding="utf-8") as f:
        f.write("\n".join(L))
    print(f"\nRelatorio salvo em {caminho_md}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--servidor", choices=["python", "cpp", "cpp_openmp", "ambos"],
                    default="ambos")
    ap.add_argument("--n", type=int, default=6, help="quantidade de sinais na sequencia")
    args = ap.parse_args()

    dir_imagens = "relatorios/imagens"
    os.makedirs(dir_imagens, exist_ok=True)
    sequencia = montar_sequencia(args.n)

    # "ambos" usa o C++ otimizado (OpenMP). Para a comparacao com a MESMA BLAS,
    # use bench_throughput.py (que mede os tres servidores).
    tipos = ["python", "cpp_openmp"] if args.servidor == "ambos" else [args.servidor]
    resumos = [rodar(t, sequencia, dir_imagens) for t in tipos]
    escrever_relatorio(resumos, sequencia, "relatorios/relatorio.md")

    # salva tambem em JSON (usado para gerar o grafico de comparacao)
    with open("relatorios/benchmark.json", "w", encoding="utf-8") as f:
        json.dump(resumos, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
