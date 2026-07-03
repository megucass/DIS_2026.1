// servidor_cpp.cpp
// =================
// Servidor de reconstrucao - VERSAO COMPILADA (C++).
//
// E' a versao do requisito "linguagem compilada e fortemente tipada". Faz o
// mesmo que o servidor Python (mesmos algoritmos, mesmo protocolo), em C++.
//
// O MESMO codigo gera DOIS executaveis, escolhendo como fazer a algebra linear:
//
//   * compilando com  -DUSAR_BLAS   -> usa a OpenBLAS (a MESMA BLAS do NumPy).
//        Comparacao 100% justa: o "motor" de calculo e' identico ao do Python.
//
//   * compilando SEM essa flag (com -fopenmp) -> usa um produto matriz-vetor
//        escrito a mao e paralelizado com OpenMP, que neste problema supera a
//        GEMV da propria OpenBLAS.
//
// Assim conseguimos mostrar os dois cenarios na apresentacao.
//
// Protocolo (identico ao servidor Python):
//   PEDIDO   ->  "ALGORITMO TAMANHO\n"  +  TAMANHO doubles (g)
//   RESPOSTA <-  "ALGO_CPP|inicio|fim|iteracoes|pixels|tempo_ms\n" + pixels doubles (f)
//             ou, se a rotina de controle de saturacao recusar o pedido:
//   RESPOSTA <-  "SATURADO|motivo\n"   (sem corpo)

#include <winsock2.h>          // sockets no Windows (Winsock)
#include <ws2tcpip.h>
#include <windows.h>           // GlobalMemoryStatusEx (rotina de controle de saturacao)
#ifdef USAR_BLAS
#include <openblas/cblas.h>    // OpenBLAS: a mesma BLAS usada pelo NumPy
#else
#include <omp.h>               // OpenMP: paraleliza os lacos em todos os nucleos
#endif
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <ctime>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

#pragma comment(lib, "ws2_32.lib")

static const char *HOST = "127.0.0.1";
#ifdef USAR_BLAS
static const int PORT = 8102;   // versao OpenBLAS
#else
static const int PORT = 8103;   // versao OpenMP
#endif

// ---------------------------------------------------------------------------
// MATRIZ: guardada como um unico vetor (linha apos linha = "row-major").
// ---------------------------------------------------------------------------
struct Matriz {
    int64_t linhas = 0, colunas = 0;
    std::vector<double> dados;            // tamanho = linhas * colunas
    double &at(int64_t i, int64_t j) { return dados[i * colunas + j]; }
    double at(int64_t i, int64_t j) const { return dados[i * colunas + j]; }
};

#ifdef USAR_BLAS
// =================== IMPLEMENTACAO 1: OpenBLAS (a mesma do NumPy) ===========
// y = H * x   via OpenBLAS (GEMV)  -- x tem tamanho 'colunas', y tem 'linhas'
std::vector<double> mult(const Matriz &H, const std::vector<double> &x) {
    std::vector<double> y(H.linhas);
    cblas_dgemv(CblasRowMajor, CblasNoTrans, (int)H.linhas, (int)H.colunas,
                1.0, H.dados.data(), (int)H.colunas, x.data(), 1, 0.0, y.data(), 1);
    return y;
}
// y = H^T * x  via OpenBLAS (GEMV transposto) -- x tem 'linhas', y tem 'colunas'
std::vector<double> mult_T(const Matriz &H, const std::vector<double> &x) {
    std::vector<double> y(H.colunas);
    cblas_dgemv(CblasRowMajor, CblasTrans, (int)H.linhas, (int)H.colunas,
                1.0, H.dados.data(), (int)H.colunas, x.data(), 1, 0.0, y.data(), 1);
    return y;
}
double prod_interno(const std::vector<double> &a, const std::vector<double> &b) {
    return cblas_ddot((int)a.size(), a.data(), 1, b.data(), 1);   // DDOT
}
double norma(const std::vector<double> &a) {
    return cblas_dnrm2((int)a.size(), a.data(), 1);               // DNRM2
}
void axpy(double alpha, const std::vector<double> &x, std::vector<double> &y) {
    cblas_daxpy((int)x.size(), alpha, x.data(), 1, y.data(), 1);  // y = y + alpha*x
}

#else
// =================== IMPLEMENTACAO 2: lacos a mao + OpenMP ==================
// y = H * x   -- cada linha e' um produto interno independente -> paraleliza
std::vector<double> mult(const Matriz &H, const std::vector<double> &x) {
    std::vector<double> y(H.linhas, 0.0);
#pragma omp parallel for schedule(static)
    for (int64_t i = 0; i < H.linhas; ++i) {
        const double *linha = &H.dados[i * H.colunas];
        double s = 0.0;
        for (int64_t j = 0; j < H.colunas; ++j) s += linha[j] * x[j];
        y[i] = s;
    }
    return y;
}
// y = H^T * x  -- cada thread acumula um parcial e somamos no fim (sem conflito)
std::vector<double> mult_T(const Matriz &H, const std::vector<double> &x) {
    std::vector<double> y(H.colunas, 0.0);
#pragma omp parallel
    {
        std::vector<double> local(H.colunas, 0.0);
#pragma omp for schedule(static) nowait
        for (int64_t i = 0; i < H.linhas; ++i) {
            const double *linha = &H.dados[i * H.colunas];
            const double xi = x[i];
            for (int64_t j = 0; j < H.colunas; ++j) local[j] += linha[j] * xi;
        }
#pragma omp critical
        for (int64_t j = 0; j < H.colunas; ++j) y[j] += local[j];
    }
    return y;
}
double prod_interno(const std::vector<double> &a, const std::vector<double> &b) {
    double s = 0.0;
    for (size_t i = 0; i < a.size(); ++i) s += a[i] * b[i];
    return s;
}
double norma(const std::vector<double> &a) { return std::sqrt(prod_interno(a, a)); }
void axpy(double alpha, const std::vector<double> &x, std::vector<double> &y) {
    for (size_t i = 0; i < x.size(); ++i) y[i] += alpha * x[i];
}
#endif

// ---------------------------------------------------------------------------
// ALGORITMO CGNE
//
// NOTA sobre o erro: o enunciado define e = ||r_(i+1)|| - ||r_i|| (sem
// modulo). Como a norma do residuo do CG e' nao-crescente, isso pararia
// sempre na 1a iteracao. Usamos |e| = std::abs(...) - a MAGNITUDE da
// variacao entre iteracoes - para o criterio funcionar como descrito
// (mesma decisao em algoritmos.py, ver o comentario la).
// ---------------------------------------------------------------------------
std::vector<double> cgne(const std::vector<double> &g, const Matriz &H,
                         int max_iter, double tol, int &iters_out) {
    std::vector<double> f(H.colunas, 0.0);
    std::vector<double> r = g;                 // r0 = g - H*0 = g
    std::vector<double> p = mult_T(H, r);      // p0 = H^T r0
    double rtr = prod_interno(r, r);
    double norma_r_ant = std::sqrt(rtr);

    int iters = 0;
    for (int k = 0; k < max_iter; ++k) {
        iters = k + 1;
        std::vector<double> Hp = mult(H, p);
        double alpha = rtr / prod_interno(p, p);
        axpy(alpha, p, f);          // f = f + alpha*p
        axpy(-alpha, Hp, r);        // r = r - alpha*(H p)

        double rtr_novo = prod_interno(r, r);
        double norma_r = std::sqrt(rtr_novo);
        if (std::abs(norma_r - norma_r_ant) < tol) break;

        double beta = rtr_novo / rtr;
        std::vector<double> Htr = mult_T(H, r);
        for (size_t i = 0; i < p.size(); ++i) p[i] = Htr[i] + beta * p[i];  // p = H^T r + beta*p
        rtr = rtr_novo;
        norma_r_ant = norma_r;
    }
    iters_out = iters;
    return f;
}

// ---------------------------------------------------------------------------
// ALGORITMO CGNR
// ---------------------------------------------------------------------------
std::vector<double> cgnr(const std::vector<double> &g, const Matriz &H,
                         int max_iter, double tol, int &iters_out) {
    std::vector<double> f(H.colunas, 0.0);
    std::vector<double> r = g;                 // r0
    std::vector<double> z = mult_T(H, r);      // z0 = H^T r0
    std::vector<double> p = z;                 // p0 = z0
    double ztz = prod_interno(z, z);
    double norma_r_ant = norma(r);

    int iters = 0;
    for (int k = 0; k < max_iter; ++k) {
        iters = k + 1;
        std::vector<double> w = mult(H, p);
        double alpha = ztz / prod_interno(w, w);
        axpy(alpha, p, f);          // f = f + alpha*p
        axpy(-alpha, w, r);         // r = r - alpha*w

        double norma_r = norma(r);
        if (std::abs(norma_r - norma_r_ant) < tol) break;

        z = mult_T(H, r);
        double ztz_novo = prod_interno(z, z);
        double beta = ztz_novo / ztz;
        for (size_t i = 0; i < p.size(); ++i) p[i] = z[i] + beta * p[i];  // p = z + beta*p
        ztz = ztz_novo;
        norma_r_ant = norma_r;
    }
    iters_out = iters;
    return f;
}

// ---------------------------------------------------------------------------
// CARREGAR A MATRIZ de um arquivo binario simples:
//   [int64 linhas][int64 colunas][linhas*colunas doubles]
// ---------------------------------------------------------------------------
Matriz carregar_bin(const std::string &caminho) {
    std::ifstream arq(caminho, std::ios::binary);
    if (!arq) throw std::runtime_error("nao abriu o binario: " + caminho);
    Matriz H;
    arq.read(reinterpret_cast<char *>(&H.linhas), sizeof(int64_t));
    arq.read(reinterpret_cast<char *>(&H.colunas), sizeof(int64_t));
    if (H.linhas <= 0 || H.colunas <= 0)
        throw std::runtime_error("dimensoes invalidas em " + caminho);
    H.dados.resize(static_cast<size_t>(H.linhas * H.colunas));
    arq.read(reinterpret_cast<char *>(H.dados.data()),
             static_cast<std::streamsize>(H.dados.size() * sizeof(double)));
    if (!arq) throw std::runtime_error("binario truncado/invalido: " + caminho);
    return H;
}

// escolhe o arquivo da matriz pelo tamanho do sinal recebido
std::string arquivo_modelo(int64_t tamanho_g) {
    if (tamanho_g == 27904) return "data/H-2.bin";   // 30x30
    if (tamanho_g == 50816) return "data/H-1.bin";   // 60x60
    return "";
}

// ---------------------------------------------------------------------------
// ROTINA DE CONTROLE DE SATURACAO (Atividade 4 do enunciado):
// mede a RAM fisica disponivel e recusa novas reconstrucoes quando ela esta
// abaixo de um minimo seguro, em vez de arriscar estourar memoria (o mesmo
// cenario testado offline em extras/simular_pouca_ram.py).
// ---------------------------------------------------------------------------
const double RAM_MINIMA_MB = 200.0;

double ram_disponivel_mb() {
    MEMORYSTATUSEX stat;
    stat.dwLength = sizeof(stat);
    GlobalMemoryStatusEx(&stat);
    return static_cast<double>(stat.ullAvailPhys) / (1024.0 * 1024.0);
}

// ---------------------------------------------------------------------------
// AUXILIARES DE REDE (ler exatamente N bytes / ler uma linha de texto)
// ---------------------------------------------------------------------------
bool receber_n(SOCKET s, char *buf, int n) {
    int lidos = 0;
    while (lidos < n) {
        int r = recv(s, buf + lidos, n - lidos, 0);
        if (r <= 0) return false;
        lidos += r;
    }
    return true;
}
// envia exatamente n bytes (send pode enviar menos que o pedido -> precisa de laco)
bool enviar_tudo(SOCKET s, const char *buf, int n) {
    int enviados = 0;
    while (enviados < n) {
        int r = send(s, buf + enviados, n - enviados, 0);
        if (r <= 0) return false;
        enviados += r;
    }
    return true;
}
std::string receber_linha(SOCKET s) {
    std::string linha;
    char c;
    while (recv(s, &c, 1, 0) == 1) {
        if (c == '\n') break;
        linha.push_back(c);
    }
    return linha;
}

std::string agora_iso() {
    using namespace std::chrono;
    auto tp = system_clock::now();
    auto ms = duration_cast<milliseconds>(tp.time_since_epoch()) % 1000;
    std::time_t t = system_clock::to_time_t(tp);
    std::tm tm{};
    localtime_s(&tm, &t);
    char buf[32];
    std::strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%S", &tm);
    char out[40];
    std::snprintf(out, sizeof(out), "%s.%03d", buf, static_cast<int>(ms.count()));
    return out;
}

// guarda as matrizes ja carregadas (carrega so uma vez)
std::map<int64_t, Matriz> g_cache;

void atender(SOCKET conn) {
    // 1) cabecalho "ALGORITMO TAMANHO"
    std::string cab = receber_linha(conn);
    auto espaco = cab.find(' ');
    if (espaco == std::string::npos) return;   // conexao de teste/vazia: ignora
    std::string algoritmo = cab.substr(0, espaco);
    int64_t tamanho = std::stoll(cab.substr(espaco + 1));

    // 2) le o sinal g (TAMANHO doubles)
    std::vector<double> g(static_cast<size_t>(tamanho));
    if (!receber_n(conn, reinterpret_cast<char *>(g.data()),
                   static_cast<int>(tamanho * 8)))
        return;

    // 2.5) rotina de controle de saturacao: recusa o pedido se a RAM livre
    // estiver abaixo do minimo seguro
    double livre = ram_disponivel_mb();
    if (livre < RAM_MINIMA_MB) {
        char msg[160];
        std::snprintf(msg, sizeof(msg), "SATURADO|RAM livre %.0fMB < minimo %.0fMB\n",
                      livre, RAM_MINIMA_MB);
        enviar_tudo(conn, msg, static_cast<int>(std::strlen(msg)));
        std::cout << "[servidor-cpp] " << msg << std::flush;
        return;
    }

    // 3) carrega a matriz (so na 1a vez) e reconstroi
    std::string caminho = arquivo_modelo(tamanho);
    if (caminho.empty())
        throw std::runtime_error("tamanho de sinal desconhecido: " +
                                 std::to_string(tamanho));
    if (g_cache.find(tamanho) == g_cache.end()) {
        std::cout << "[servidor-cpp] carregando " << caminho << " ...\n"
                  << std::flush;
        g_cache[tamanho] = carregar_bin(caminho);
    }
    const Matriz &H = g_cache[tamanho];

    std::string inicio = agora_iso();
    auto t0 = std::chrono::high_resolution_clock::now();
    int iters = 0;
    std::vector<double> f = (algoritmo == "CGNE")
                                ? cgne(g, H, 10, 1e-4, iters)
                                : cgnr(g, H, 10, 1e-4, iters);
    double tempo_ms = std::chrono::duration<double, std::milli>(
                          std::chrono::high_resolution_clock::now() - t0).count();
    std::string fim = agora_iso();

    // 4) responde: cabecalho com metadados + imagem
    char cabresp[160];
    std::snprintf(cabresp, sizeof(cabresp), "%s_CPP|%s|%s|%d|%lld|%.3f\n",
                  algoritmo.c_str(), inicio.c_str(), fim.c_str(), iters,
                  static_cast<long long>(f.size()), tempo_ms);
    enviar_tudo(conn, cabresp, static_cast<int>(std::strlen(cabresp)));
    enviar_tudo(conn, reinterpret_cast<const char *>(f.data()),
                static_cast<int>(f.size() * sizeof(double)));
    std::cout << "[servidor-cpp] " << algoritmo << " -> " << iters
              << " iter, " << tempo_ms << " ms\n" << std::flush;
}

int main() {
    WSADATA wsa;
    WSAStartup(MAKEWORD(2, 2), &wsa);

    SOCKET servidor = socket(AF_INET, SOCK_STREAM, 0);
    int sim = 1;
    setsockopt(servidor, SOL_SOCKET, SO_REUSEADDR,
               reinterpret_cast<char *>(&sim), sizeof(sim));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(PORT);
    inet_pton(AF_INET, HOST, &addr.sin_addr);
    bind(servidor, reinterpret_cast<sockaddr *>(&addr), sizeof(addr));
    listen(servidor, 8);
#ifdef USAR_BLAS
    std::cout << "[servidor-cpp] pronto em " << HOST << ":" << PORT
              << "  (OpenBLAS: " << openblas_get_num_threads() << " threads)\n"
              << std::flush;
#else
    std::cout << "[servidor-cpp] pronto em " << HOST << ":" << PORT
              << "  (OpenMP: " << omp_get_max_threads() << " threads)\n"
              << std::flush;
#endif

    while (true) {
        SOCKET conn = accept(servidor, nullptr, nullptr);
        if (conn == INVALID_SOCKET) continue;
        try {
            atender(conn);           // try/catch para um pedido ruim nao derrubar o servidor
        } catch (const std::exception &e) {
            std::cerr << "[servidor-cpp] erro: " << e.what() << "\n";
        }
        closesocket(conn);
    }
    WSACleanup();   // (nunca chega aqui; fica para documentar o encerramento)
    return 0;
}
