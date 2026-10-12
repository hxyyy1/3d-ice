#!/bin/bash
# Install SuperLU

echo "Install SuperLU_MT"
unzip superlu_mt-4.0.0.zip
cd superlu_mt-4.0.0/
cp MAKE_INC/make.linux.openmp make.inc


# 1) Enable vendor BLAS
sed -i 's/^BLASDEF.*/BLASDEF   = -DUSE_VENDOR_BLAS/' make.inc

# 2) Use the linker search path (override BLASLIB for a custom installation).
sed -i 's@^BLASLIB .*@BLASLIB = -lopenblas@' make.inc

# 3) Fortran naming convention: routines have a trailing underscore
sed -i 's/^CDEFS.*/CDEFS        = -DAdd_/' make.inc

# Release the ordering workspace even for a diagonal matrix.
patch --forward -p1 < ../patches/superlu_mt-4.0.0-empty-ordering-cleanup.patch || exit 1

#Build SuperLU
make
