"""
bench_throughput.py
==================
Comparacao de DESEMPENHO dos tres servidores na reconstrucao de imagem:
    - Python  (NumPy / OpenBLAS)
    - C++     (OpenBLAS)   -> a MESMA BLAS do NumPy (comparacao mais justa)
    - C++     (OpenMP)     -> produto matriz-vetor proprio, paralelizado

Metrica: tempo MEDIANO por imagem (do solver), medido sob carga leve -- com uma
pequena pausa entre os pedidos, igual ao cliente real (que envia em intervalos
aleatorios). Isso evita o "estrangulamento termico" de rajadas e da numeros
estaveis e representativos. Salva em relatorios/throughput.json.
"""

import json
import os
import statistics
import time

import cliente
import algoritmos as alg

N = int(os.environ.get("N", "15"))          # imagens medidas por servidor
SINAL = "g-30x30-1.csv"


def medir(tipo):
    g = alg.aplicar_ganho(alg.carregar_sinal(os.path.join("data", SINAL)))
    proc = cliente.iniciar_servidor(tipo)
    porta = cliente.PORTAS[tipo]
    try:
        cliente.reconstruir(porta, "CGNR", g)            # aquecimento (carrega H)
        solver = []
        for _ in range(N):
            time.sleep(0.15)                             # carga leve (como o cliente real)
            meta, _ = cliente.reconstruir(porta, "CGNR", g)
            solver.append(meta["tempo_solver_ms"])
    finally:
        cliente.parar_servidor(proc)
    mediano = statistics.median(solver)
    return {
        "tipo": tipo,
        "n": N,
        "ms_por_img": mediano,             # tempo mediano por imagem (solver)
        "throughput_img_s": 1000.0 / mediano,
    }


def main():
    os.makedirs("relatorios", exist_ok=True)
    resultados = {}
    for tipo in ["python", "cpp", "cpp_openmp"]:
        r = medir(tipo)
        resultados[tipo] = r
        print(f"{tipo:>11}: tempo mediano por imagem {r['ms_por_img']:6.1f} ms  "
              f"({r['throughput_img_s']:.1f} img/s)")

    with open("relatorios/throughput.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    py = resultados["python"]["ms_por_img"]
    print(f"\n  C++ OpenBLAS (mesma BLAS) vs Python: "
          f"{(py / resultados['cpp']['ms_por_img'] - 1) * 100:+.0f}%")
    print(f"  C++ OpenMP   (paralelizado) vs Python: "
          f"{(py / resultados['cpp_openmp']['ms_por_img'] - 1) * 100:+.0f}%")


if __name__ == "__main__":
    main()
