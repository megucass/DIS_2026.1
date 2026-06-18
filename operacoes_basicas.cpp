// operacoes_basicas.cpp
// =====================
// Atividade 2 do enunciado, versao C++ (compilada).
//
//     MN = M * N      (matriz x matriz)
//     aM = a * M      (vetor x matriz)
//     Ma = M * a      (matriz x vetor)
//
// Le M, N, a de data/ops/ (separador ';') e confere com os gabaritos.
// Tudo com std::vector, sem bibliotecas externas, para ficar didatico.

#include <cmath>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

using Matriz = std::vector<std::vector<double>>;

// le um CSV com separador ';' em uma matriz (linhas x colunas)
Matriz ler_csv(const std::string &caminho) {
    Matriz m;
    std::ifstream arq(caminho);
    std::string linha;
    while (std::getline(arq, linha)) {
        if (linha.empty()) continue;
        std::vector<double> valores;
        std::stringstream ss(linha);
        std::string celula;
        while (std::getline(ss, celula, ';'))
            if (!celula.empty()) valores.push_back(std::stod(celula));
        if (!valores.empty()) m.push_back(valores);
    }
    return m;
}

bool quase_igual(const std::vector<double> &x, const std::vector<double> &y) {
    // tolerancia de 0.01: o gabarito foi salvo com apenas 2 casas decimais
    if (x.size() != y.size()) return false;
    for (size_t i = 0; i < x.size(); ++i)
        if (std::abs(x[i] - y[i]) > 1e-2) return false;
    return true;
}

int main() {
    Matriz M = ler_csv("data/ops/M.csv");      // 10x10
    Matriz N = ler_csv("data/ops/N.csv");      // 10x10
    std::vector<double> a = ler_csv("data/ops/a.csv")[0];  // vetor de 10
    const int n = static_cast<int>(M.size());

    // MN = M * N
    Matriz MN(n, std::vector<double>(n, 0.0));
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            for (int k = 0; k < n; ++k) MN[i][j] += M[i][k] * N[k][j];

    // aM = a * M   (vetor linha x matriz)
    std::vector<double> aM(n, 0.0);
    for (int j = 0; j < n; ++j)
        for (int i = 0; i < n; ++i) aM[j] += a[i] * M[i][j];

    // Ma = M * a   (matriz x vetor coluna)
    std::vector<double> Ma(n, 0.0);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j) Ma[i] += M[i][j] * a[j];

    std::cout << "M: " << n << "x" << n << "   a: " << a.size() << "\n";
    std::cout << "aM = a*M -> ";
    for (double v : aM) std::cout << v << " ";
    std::cout << "\nMa = M*a -> ";
    for (double v : Ma) std::cout << v << " ";
    std::cout << "\n";

    // confere com os gabaritos (matriz MN inteira, como na versao Python)
    Matriz MN_ref = ler_csv("data/ops/MN.csv");
    std::vector<double> aM_ref = ler_csv("data/ops/aM.csv")[0];
    bool aM_ok = quase_igual(aM, aM_ref);
    bool MN_ok = (MN.size() == MN_ref.size());
    for (size_t i = 0; i < MN.size() && MN_ok; ++i)
        MN_ok = quase_igual(MN[i], MN_ref[i]);
    std::cout << "\naM confere com o gabarito? " << (aM_ok ? "sim" : "nao") << "\n";
    std::cout << "MN confere com o gabarito? " << (MN_ok ? "sim" : "nao") << "\n";
    return 0;
}
