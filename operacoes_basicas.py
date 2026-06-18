"""
operacoes_basicas.py
===================
Atividade 2 do enunciado: testar as operacoes basicas de algebra linear
usando a biblioteca escolhida (NumPy, que usa BLAS por baixo).

    MN = M * N      (matriz x matriz)
    aM = a * M      (vetor x matriz)
    Ma = M * a      (matriz x vetor)

Os dados (M, N, a) e os gabaritos (MN, aM) vem de data/ops/ (do Dados.zip).
Usamos ';' como separador (formato do arquivo).
"""

import os
import numpy as np

OPS = "data/ops"


def carregar(nome):
    return np.loadtxt(os.path.join(OPS, nome), delimiter=";")


def main():
    M = carregar("M.csv")          # 10 x 10
    N = carregar("N.csv")          # 10 x 10
    a = carregar("a.csv")          # vetor de 10

    MN = M @ N                     # multiplicacao de matrizes
    aM = a @ M                     # vetor (linha) x matriz
    Ma = M @ a                     # matriz x vetor (coluna)

    print("M:", M.shape, " N:", N.shape, " a:", a.shape)
    print("MN = M*N -> shape", MN.shape)
    print("aM = a*M ->", np.round(aM, 2))
    print("Ma = M*a ->", np.round(Ma, 2))

    # confere com os gabaritos fornecidos
    # (o gabarito foi salvo com 2 casas decimais, por isso a tolerancia de 0.01)
    MN_ok = np.allclose(MN, carregar("MN.csv"), atol=1e-2)
    aM_ok = np.allclose(aM, carregar("aM.csv"), atol=1e-2)
    print(f"\nMN confere com o gabarito? {MN_ok}")
    print(f"aM confere com o gabarito? {aM_ok}")


if __name__ == "__main__":
    main()
