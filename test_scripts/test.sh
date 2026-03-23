g++ -march=rv64gcv -mabi=lp64d cpu_rvv.cpp -o cpu_rvv

objdump -d cpu_rvv | grep '^ *[0-9a-f]*:.*v'