# compilar.ps1
# ============
# Compila os dois programas C++ com o g++ do MSYS2/MinGW.
# Usa -static para o .exe rodar sozinho (sem precisar das DLLs do MinGW no PATH).

$ErrorActionPreference = "Stop"
$mingw = "C:\msys64\mingw64\bin"
$gpp = "$mingw\g++.exe"
if (-not (Test-Path $gpp)) { throw "g++ nao encontrado em $gpp" }
# o g++ precisa do seu proprio bin no PATH para achar cc1plus / linker
$env:PATH = "$mingw;$env:PATH"

Write-Host "Compilando servidor_cpp.exe (OpenBLAS - a mesma BLAS do NumPy) ..."
# -DUSAR_BLAS + -lopenblas: usa a OpenBLAS | -O2 -march=native: otimizacao + SIMD
& $gpp -O2 -march=native -std=c++17 -DUSAR_BLAS servidor_cpp.cpp -o servidor_cpp.exe -lopenblas -lws2_32
if ($LASTEXITCODE -ne 0) { throw "falha ao compilar servidor_cpp.cpp (OpenBLAS)" }
# copia as DLLs necessarias para o exe da OpenBLAS rodar sozinho
foreach ($dll in 'libopenblas.dll','libgcc_s_seh-1.dll','libstdc++-6.dll','libwinpthread-1.dll','libgfortran-5.dll','libquadmath-0.dll','libgomp-1.dll') {
    $src = Join-Path $mingw $dll
    if (Test-Path $src) { Copy-Item $src -Destination . -Force }
}

Write-Host "Compilando servidor_cpp_openmp.exe (lacos a mao + OpenMP) ..."
# sem -DUSAR_BLAS, com -fopenmp: usa a implementacao paralela escrita a mao
& $gpp -O2 -march=native -fopenmp -std=c++17 -static servidor_cpp.cpp -o servidor_cpp_openmp.exe -lws2_32
if ($LASTEXITCODE -ne 0) { throw "falha ao compilar servidor_cpp.cpp (OpenMP)" }

Write-Host "Compilando operacoes_basicas.exe ..."
& $gpp -O2 -std=c++17 -static operacoes_basicas.cpp -o operacoes_basicas.exe
if ($LASTEXITCODE -ne 0) { throw "falha ao compilar operacoes_basicas.cpp" }

Write-Host "Compilando extras/experimento_memoria.exe (streaming + float32) ..."
& $gpp -O2 -march=native -std=c++17 -static extras/experimento_memoria.cpp -o extras/experimento_memoria.exe -lpsapi
if ($LASTEXITCODE -ne 0) { throw "falha ao compilar extras/experimento_memoria.cpp" }

Write-Host "OK. Gerados: servidor_cpp.exe, servidor_cpp_openmp.exe, operacoes_basicas.exe, extras/experimento_memoria.exe"
