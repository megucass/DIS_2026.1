// experimento_memoria.cpp
// =======================
// EXPERIMENTO SEPARADO (versao C++): reconstrucao com MUITO POUCA memoria.
//
// Le a matriz H do disco EM BLOCOS, em float32 (mesmos arquivos .f32.bin que o
// Python usa), e faz o CGNR sem nunca segurar a matriz inteira na RAM. No fim,
// reporta o PICO de memoria do processo (WinAPI) e o tempo.
//
// Uso:  experimento_memoria.exe 30x30   |   experimento_memoria.exe 60x60

#include <windows.h>
#include <psapi.h>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

#pragma comment(lib, "psapi.lib")

// pico de memoria do processo, em MB
double pico_ram_mb() {
    PROCESS_MEMORY_COUNTERS c;
    GetProcessMemoryInfo(GetCurrentProcess(), &c, sizeof(c));
    return c.PeakWorkingSetSize / 1e6;
}

// le o sinal g (um valor por linha) e aplica o ganho (igual ao Python)
std::vector<float> ler_sinal_com_ganho(const std::string &path, int n_sensores = 64) {
    std::vector<float> g;
    std::ifstream f(path);
    std::string linha;
    while (std::getline(f, linha)) {
        if (!linha.empty()) g.push_back(std::stof(linha));
    }
    const int S = (int)g.size() / n_sensores;            // amostras por sensor
    for (size_t k = 0; k < g.size(); ++k) {
        int l = (int)(k % S) + 1;                        // indice da amostra (ordem Fortran)
        g[k] *= (float)(100.0 + (1.0 / 20.0) * l * std::sqrt((double)l));
    }
    return g;
}

double prod(const std::vector<float> &a, const std::vector<float> &b) {
    double s = 0.0;
    for (size_t i = 0; i < a.size(); ++i) s += (double)a[i] * b[i];
    return s;
}

// w = H * p, lendo H em blocos de 'bloco' linhas
std::vector<float> mat_stream(const std::string &path, int m, int n,
                              const std::vector<float> &p, int bloco) {
    std::vector<float> w(m), buf((size_t)bloco * n);
    std::ifstream fh(path, std::ios::binary);
    fh.seekg(16);
    int i = 0;
    while (i < m) {
        int b = std::min(bloco, m - i);
        fh.read(reinterpret_cast<char *>(buf.data()), (std::streamsize)b * n * 4);
        for (int row = 0; row < b; ++row) {
            const float *lin = &buf[(size_t)row * n];
            double s = 0.0;
            for (int j = 0; j < n; ++j) s += (double)lin[j] * p[j];
            w[i + row] = (float)s;
        }
        i += b;
    }
    return w;
}

// z = H^T * r, lendo H em blocos de 'bloco' linhas e acumulando
std::vector<float> matT_stream(const std::string &path, int m, int n,
                               const std::vector<float> &r, int bloco) {
    std::vector<float> z(n, 0.0f), buf((size_t)bloco * n);
    std::ifstream fh(path, std::ios::binary);
    fh.seekg(16);
    int i = 0;
    while (i < m) {
        int b = std::min(bloco, m - i);
        fh.read(reinterpret_cast<char *>(buf.data()), (std::streamsize)b * n * 4);
        for (int row = 0; row < b; ++row) {
            const float *lin = &buf[(size_t)row * n];
            const float ri = r[i + row];
            for (int j = 0; j < n; ++j) z[j] += lin[j] * ri;
        }
        i += b;
    }
    return z;
}

int main(int argc, char **argv) {
    std::string modelo = (argc > 1) ? argv[1] : "30x30";
    int bloco = (argc > 2) ? std::atoi(argv[2]) : 512;   // linhas lidas por vez
    if (bloco < 1) bloco = 1;
    std::string prefixo = (modelo == "60x60") ? "H-1" : "H-2";
    std::string sinal = (modelo == "60x60") ? "G-1.csv" : "g-30x30-1.csv";
    std::string path = "../data/" + prefixo + ".f32.bin";

    int64_t rows, cols;
    {
        std::ifstream fh(path, std::ios::binary);
        if (!fh) { std::fprintf(stderr, "nao abriu %s\n", path.c_str()); return 1; }
        fh.read(reinterpret_cast<char *>(&rows), 8);
        fh.read(reinterpret_cast<char *>(&cols), 8);
    }
    int m = (int)rows, n = (int)cols;
    std::vector<float> g = ler_sinal_com_ganho("../data/" + sinal);

    auto t0 = std::chrono::high_resolution_clock::now();
    // CGNR streaming float32
    std::vector<float> f(n, 0.0f), r = g;
    std::vector<float> z = matT_stream(path, m, n, r, bloco);
    std::vector<float> p = z;
    double ztz = prod(z, z);
    double norma_r_ant = std::sqrt(prod(r, r));
    int iters = 0;
    for (int k = 0; k < 10; ++k) {
        iters = k + 1;
        std::vector<float> w = mat_stream(path, m, n, p, bloco);
        float alpha = (float)(ztz / prod(w, w));
        for (int j = 0; j < n; ++j) f[j] += alpha * p[j];   // in-place
        for (int i = 0; i < m; ++i) r[i] -= alpha * w[i];   // in-place
        double norma_r = std::sqrt(prod(r, r));
        if (std::abs(norma_r - norma_r_ant) < 1e-4) break;
        z = matT_stream(path, m, n, r, bloco);
        double ztz_novo = prod(z, z);
        float beta = (float)(ztz_novo / ztz);
        for (int j = 0; j < n; ++j) p[j] = z[j] + beta * p[j];
        ztz = ztz_novo;
        norma_r_ant = norma_r;
    }
    double dt = std::chrono::duration<double, std::milli>(
                    std::chrono::high_resolution_clock::now() - t0).count();

    // linha parseavel: RESULT|pico_mb|tempo_ms|norma|iters
    std::printf("RESULT|%.1f|%.1f|%.4g|%d\n", pico_ram_mb(), dt, std::sqrt(prod(f, f)), iters);
    return 0;
}
