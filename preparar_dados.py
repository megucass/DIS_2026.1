"""
preparar_dados.py
=================
Passo unico de preparacao. Faz duas coisas:

  1) Descompacta as matrizes H (H-1.csv.zip, H-2.csv.zip) e cria o cache .npy
     usado pelo servidor Python.
  2) Cria um cache binario simples (.bin) usado pelo servidor C++:
        [int64 linhas][int64 colunas][linhas*colunas doubles, row-major]

Rode isto UMA vez antes de usar os servidores.
"""

import os
import struct
import zipfile

import numpy as np

DATA = "data"
MODELOS = [("H-2.csv.zip", "H-2.csv"), ("H-1.csv.zip", "H-1.csv")]


def descompactar(zip_nome, csv_nome):
    destino = os.path.join(DATA, csv_nome)
    if os.path.exists(destino) or os.path.exists(destino + ".npy"):
        return destino
    print(f"[prep] descompactando {zip_nome} ...")
    with zipfile.ZipFile(os.path.join(DATA, zip_nome)) as zf:
        with zf.open(csv_nome) as src, open(destino, "wb") as dst:
            dst.write(src.read())
    return destino


def carregar_npy(csv_nome):
    npy = os.path.join(DATA, csv_nome + ".npy")
    if os.path.exists(npy):
        return np.load(npy)
    print(f"[prep] convertendo {csv_nome} para .npy (pode demorar) ...")
    H = np.loadtxt(os.path.join(DATA, csv_nome), delimiter=",")
    np.save(npy, H)
    return H


def gravar_bin(H, csv_nome):
    """Grava H em binario para o C++ ler rapido."""
    caminho = os.path.join(DATA, csv_nome.replace(".csv", ".bin"))
    H = np.ascontiguousarray(H, dtype="<f8")   # garante row-major, float64
    with open(caminho, "wb") as f:
        f.write(struct.pack("<qq", H.shape[0], H.shape[1]))  # 2 int64
        f.write(H.tobytes())
    print(f"[prep] {caminho}  ({H.shape[0]}x{H.shape[1]})")


def main():
    for zip_nome, csv_nome in MODELOS:
        descompactar(zip_nome, csv_nome)
        H = carregar_npy(csv_nome)
        gravar_bin(H, csv_nome)
    print("[prep] pronto.")


if __name__ == "__main__":
    main()
