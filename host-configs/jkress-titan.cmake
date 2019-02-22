###############################################################################
# Copyright (c) 2015-2018, Lawrence Livermore National Security, LLC.
# 
# Produced at the Lawrence Livermore National Laboratory
# 
# LLNL-CODE-716457
# 
# All rights reserved.
# 
# This file is part of Ascent. 
# 
# For details, see: http://ascent.readthedocs.io/.
# 
# Please also read ascent/LICENSE
# 
# Redistribution and use in source and binary forms, with or without 
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, 
#   this list of conditions and the disclaimer below.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the disclaimer (as noted below) in the
#   documentation and/or other materials provided with the distribution.
# 
# * Neither the name of the LLNS/LLNL nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL LAWRENCE LIVERMORE NATIONAL SECURITY,
# LLC, THE U.S. DEPARTMENT OF ENERGY OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
# DAMAGES  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, 
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE 
# POSSIBILITY OF SUCH DAMAGE.
# 
###############################################################################

set(CMAKE_BUILD_TYPE "Release" CACHE PATH "")

# c compiler
set(CMAKE_C_COMPILER "/opt/cray/craype/2.5.13/bin/cc" CACHE PATH "")
set(C_COMPILE_FLAGS "-fPIC" CACHE PATH "")

# cpp compiler
set(CMAKE_CXX_COMPILER "/opt/cray/craype/2.5.13/bin/CC" CACHE PATH "")
set(CXX_COMPILE_FLAGS "-fPIC" CACHE PATH "")

# fortran compiler (need for cloverleaf)
set(ENABLE_FORTRAN ON CACHE PATH "")
set(CMAKE_Fortran_COMPILER  "/opt/cray/craype/2.5.13/bin/ftn" CACHE PATH "")

# OPENMP (optional: for proxy apps)
set(ENABLE_OPENMP ON CACHE PATH "")

# MPI Support
set(ENABLE_MPI  ON CACHE PATH "")

set(MPI_C_COMPILER  "/opt/cray/craype/2.5.13/bin/cc" CACHE PATH "")
set(MPI_C_COMPILE_FLAGS "-fPIC" CACHE PATH "")

set(MPI_CXX_COMPILER "/opt/cray/craype/2.5.13/bin/CC" CACHE PATH "")
set(MPI_CXX_COMPILE_FLAGS "-fPIC" CACHE PATH "")

set(MPI_Fortran_COMPILER "/opt/cray/craype/2.5.13/bin/ftn" CACHE PATH "")

set(MPIEXEC "/opt/cray/alps/5.2.4-2.0502.9950.37.1.gem/bin/aprun" CACHE PATH "")

set(MPIEXEC_NUMPROC_FLAG -n CACHE PATH "")

##no shared libs
set(BUILD_SHARED_LIBS OFF CACHE PATH "")
set(ENABLE_SHARED_LIBS OFF CACHE PATH "")

##python
set(PYTHON_DIR "/sw/xk6/python/2.7.9/sles11.3_gnu4.3.4/" CACHE PATH "")
set(ENABLE_PYTHON OFF CACHE PATH "")



# CUDA support
#set(ENABLE_CUDA ON CACHE PATH "")

# NO CUDA Support
set(ENABLE_CUDA OFF CACHE PATH "")


# conduit 
set(ASCENT_DIR "/lustre/atlas2/csc143/proj-shared/jkress/ascent-files/ompBuild/ascent/install-release" CACHE PATH "")

# conduit 
set(CONDUIT_DIR "/lustre/atlas2/csc143/proj-shared/jkress/ascent-files/ompBuild/conduit/install" CACHE PATH "")

# icet 
set(ICET_DIR "/disk2TB/proj/alpine/icet/install" CACHE PATH "")

#vtk-h
set(VTKH_DIR "/lustre/atlas2/csc143/proj-shared/jkress/ascent-files/ompBuild/vtk-h/install" CACHE PATH "")

#
# vtkm
#

# tbb
set(ASCENT_VTKM_USE_TBB OFF CACHE PATH "")
#set(TBB_DIR "/usr/include" CACHE PATH "")

# vtkm
set(VTKM_DIR "/lustre/atlas2/csc143/proj-shared/jkress/ascent-files/ompBuild/vtk-m/install" CACHE PATH "")

# HDF5 support (optional)
# hdf5
set(HDF5_DIR "/opt/cray/hdf5/1.10.0.3/gnu/4.9" CACHE PATH "")
set(HDF5_INCLUDE_DIRS "/opt/cray/hdf5/1.10.0.3/gnu/4.9/include" CACHE PATH "")

set(ADIOS_DIR "/lustre/atlas2/csc143/proj-shared/jkress/ascent-files/ADIOS/install.xk6.gnu" CACHE PATH "")

#SPHINX documentation building
#set("SPHINX_EXECUTABLE" "/path/to/sphinx-build" CACHE PATH "")

##################################
# end boilerplate host-config
##################################
