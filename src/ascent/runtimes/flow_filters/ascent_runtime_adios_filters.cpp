//~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~//
// Copyright (c) 2015-2019, Lawrence Livermore National Security, LLC.
//
// Produced at the Lawrence Livermore National Laboratory
//
// LLNL-CODE-716457
//
// All rights reserved.
//
// This file is part of Ascent.
//
// For details, see: http://ascent.readthedocs.io/.
//
// Please also read ascent/LICENSE
//
// Redistribution and use in source and binary forms, with or without
// modification, are permitted provided that the following conditions are met:
//
// * Redistributions of source code must retain the above copyright notice,
//   this list of conditions and the disclaimer below.
//
// * Redistributions in binary form must reproduce the above copyright notice,
//   this list of conditions and the disclaimer (as noted below) in the
//   documentation and/or other materials provided with the distribution.
//
// * Neither the name of the LLNS/LLNL nor the names of its contributors may
//   be used to endorse or promote products derived from this software without
//   specific prior written permission.
//
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
// AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
// IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
// ARE DISCLAIMED. IN NO EVENT SHALL LAWRENCE LIVERMORE NATIONAL SECURITY,
// LLC, THE U.S. DEPARTMENT OF ENERGY OR CONTRIBUTORS BE LIABLE FOR ANY
// DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
// DAMAGES  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
// OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
// HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
// STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
// IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
// POSSIBILITY OF SUCH DAMAGE.
//
//~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~//

/******************************************************
TODO:

 */


//-----------------------------------------------------------------------------
///
/// file: ascent_runtime_adios_filters.cpp
///
//-----------------------------------------------------------------------------

#include "ascent_runtime_adios_filters.hpp"

//-----------------------------------------------------------------------------
// thirdparty includes
//-----------------------------------------------------------------------------

// conduit includes
#include <conduit.hpp>

//-----------------------------------------------------------------------------
// ascent includes
//-----------------------------------------------------------------------------
#include <ascent_logging.hpp>
#include <ascent_file_system.hpp>

#include <flow_graph.hpp>
#include <flow_workspace.hpp>

// mpi related includes

#ifdef ASCENT_MPI_ENABLED
#include <mpi.h>
#else
#include <mpidummy.h>
#define _NOMPI
#endif

#include <adios.h>
#include <adios_read.h>
#include <adios_error.h>

#include <set>
#include <cstring>
#include <limits>
#include <cmath>

using namespace std;
using namespace conduit;
using namespace flow;

struct coordInfo
{
    coordInfo(int r, int n, double r0, double r1) : num(n), rank(r) {range[0]=r0; range[1]=r1;}
    coordInfo() {num=0; rank=-1; range[0]=range[1]=0;}
    coordInfo(const coordInfo &c) {num=c.num; rank=c.rank; range[0]=c.range[0]; range[1]=c.range[1];}

    int num, rank;
    double range[2];
};

inline bool operator<(const coordInfo &c1, const coordInfo &c2)
{
    return c1.range[0] < c2.range[0];
}

inline ostream& operator<<(ostream &os, const coordInfo &ci)
{
    os<<"(r= "<<ci.rank<<" : n= "<<ci.num<<" ["<<ci.range[0]<<","<<ci.range[1]<<"])";
    return os;
}

template <class T>
inline std::ostream& operator<<(ostream& os, const vector<T>& v)
{
    os<<"[";
    auto it = v.begin();
    for ( ; it != v.end(); ++it)
        os<<" "<< *it;
    os<<"]";
    return os;
}

template <class T>
inline ostream& operator<<(ostream& os, const set<T>& s)
{
    os<<"{";
    auto it = s.begin();
    for ( ; it != s.end(); ++it)
        os<<" "<< *it;
    os<<"}";
    return os;
}

//-----------------------------------------------------------------------------
// -- begin ascent:: --
//-----------------------------------------------------------------------------
namespace ascent
{

//-----------------------------------------------------------------------------
// -- begin ascent::runtime --
//-----------------------------------------------------------------------------
namespace runtime
{

//-----------------------------------------------------------------------------
// -- begin ascent::runtime::filters --
//-----------------------------------------------------------------------------
namespace filters
{

//-----------------------------------------------------------------------------
ADIOS::ADIOS()
    :Filter()
{
    mpi_comm = 0;
    rank = 0;
    numRanks = 1;
    meshName = "mesh";
    step = 0;

    globalDims.resize(4);
    localDims.resize(4);
    offset.resize(4);
    for (int i = 0; i < 4; i++)
        globalDims[i] = localDims[i] = offset[i] = 0;

    localDimsCon.resize(1);
    localDimsCon[0] = 0;
    globalDimsCon.resize(1);
    globalDimsCon[0] = 0;
    offsetCon.resize(1);
    offsetCon[0] = 0;


#ifdef ASCENT_MPI_ENABLED
    mpi_comm = MPI_Comm_f2c(Workspace::default_mpi_comm());
    MPI_Comm_rank(mpi_comm, &rank);
    MPI_Comm_size(mpi_comm, &numRanks);
#endif
    globalDims[0] = numRanks;
    localDims[0] = 1;
    offset[0] = rank;
    explicitMesh = false;
}

//-----------------------------------------------------------------------------
ADIOS::~ADIOS()
{
// empty
}

//-----------------------------------------------------------------------------
void
ADIOS::declare_interface(Node &i)
{
    i["type_name"]   = "adios";
    i["port_names"].append() = "in";
    i["output_port"] = "false";
}

//-----------------------------------------------------------------------------
bool
ADIOS::verify_params(const conduit::Node &params,
                     conduit::Node &info)
{
    bool res = true;

    if (!params.has_child("transport") ||
        !params["transport"].dtype().is_string())
    {
        info["errors"].append() = "missing required entry 'transport'";
        res = false;
    }


    if (!params.has_child("filename") ||
        !params["transport"].dtype().is_string() )
    {
        info["errors"].append() = "missing required entry 'filename'";
        res = false;
    }

    return res;
}

//-----------------------------------------------------------------------------
void
ADIOS::execute()
{
    if(!input(0).check_type<Node>())
    {
        // error
        ASCENT_ERROR("ERROR: adios filter requires a conduit::Node input");
    }

    transportType = params()["transport"].as_string();
    fileName      = params()["filename"].as_string();
    vector<string> variables;

    if (params().has_child("variables"))
    {
        string str = params()["variables"].as_string();
        stringstream ss(str);
        string s;
        while (ss >> s)
        {
            if (s.size() == 0)
                continue;
            if (s[s.size()-1] == ',')
                s = s.substr(0, s.size()-1);
            variables.push_back(s);
            ss.ignore(1);
        }
    }

    const string groupName = "ascent";

    // get params
    if (transportType == "file")
    {
        //set mpi option based on num ranks, with more ranks we need to aggregate
        string adiosOpt, mpiMethod;
        if(numRanks > 10000)
        {
            mpiMethod = "MPI_AGGREGATE";
            adiosOpt ="num_aggregators=1000,random_offset=1,striping_count=1,have_metadata_file=1";
        }
        else
        {
            mpiMethod = "MPI";
            adiosOpt = "";
        }

        adios_init_noxml(mpi_comm);
        adios_declare_group(&adiosGroup, groupName.c_str(), "iter", adios_stat_default);
        adios_select_method(adiosGroup,
                            mpiMethod.c_str(),
                            adiosOpt.c_str(),
                            "");
        adios_open(&adiosFile, groupName.c_str(), fileName.c_str(), "w", mpi_comm);
    }
    else if (transportType == "dataspaces")
    {
        if (step == 0)
        {
            int rc = adios_read_init_method(ADIOS_READ_METHOD_DATASPACES, mpi_comm, "verbose=0");
            if (rc != 0)
                ASCENT_ERROR("ADIOS Error: "<<adios_errmsg());

            adios_init_noxml(mpi_comm);
            adios_declare_group(&adiosGroup, groupName.c_str(), "", adios_stat_default);
            adios_select_method(adiosGroup, "DATASPACES", "", "");
            adios_define_mesh_timevarying("no", adiosGroup, meshName.c_str());
        }

        //adios_open(&adiosFile, groupName.c_str(), fileName.c_str(), (step==0?"w":"a"), mpi_comm);
        adios_open(&adiosFile, groupName.c_str(), fileName.c_str(), "w", mpi_comm);
    }
    else if (transportType == "dimes")
    {
        if (step == 0)
        {
            int rc = adios_read_init_method(ADIOS_READ_METHOD_DIMES, mpi_comm, "verbose=0");
            if (rc != 0)
                ASCENT_ERROR("ADIOS Error: "<<adios_errmsg());

            adios_init_noxml(mpi_comm);
            adios_declare_group(&adiosGroup, groupName.c_str(), "", adios_stat_default);
            adios_select_method(adiosGroup, "DIMES", "", "");
            adios_define_mesh_timevarying("no", adiosGroup, meshName.c_str());
        }

        //adios_open(&adiosFile, groupName.c_str(), fileName.c_str(), (step==0?"w":"a"), mpi_comm);
        adios_open(&adiosFile, groupName.c_str(), fileName.c_str(), "w", mpi_comm);
    }
   else if (transportType == "flexpath")
    {
        if (step == 0)
        {
            int rc = adios_read_init_method(ADIOS_READ_METHOD_FLEXPATH, mpi_comm, "verbose=0");
            if (rc != 0)
                ASCENT_ERROR("ADIOS Error: "<<adios_errmsg());

            adios_init_noxml(mpi_comm);
            adios_declare_group(&adiosGroup, groupName.c_str(), "", adios_stat_default);
            adios_select_method(adiosGroup, "FLEXPATH", "", "");
            adios_define_mesh_timevarying("no", adiosGroup, meshName.c_str());
        }

        //adios_open(&adiosFile, groupName.c_str(), fileName.c_str(), (step==0?"w":"a"), mpi_comm);
        adios_open(&adiosFile, groupName.c_str(), fileName.c_str(), "w", mpi_comm);
    }
    else
    {
        ASCENT_ERROR("ERROR: Unsupported transport type");
    }

    adios_define_schema_version(adiosGroup, (char*)"1.1");

    //Fetch input data
    //!! Assuming a single domain
    Node *node_input = input<Node>(0);
    Node &child_domain = node_input->child(0);

//if(rank == 0)
//{
//   cerr << "Printing main node schema" << endl;
//    node_input->schema().print();
    //cerr << endl;
//}


    NodeConstIterator itr = child_domain["coordsets"].children();
    NodeConstIterator topoItr = child_domain["topologies"].children();
    while (itr.has_next() && topoItr.has_next())
    {
        const Node &coordSet = itr.next();
        const Node &topoSet = topoItr.next();
        std::string coordSetType = coordSet["type"].as_string();

        if (coordSetType == "uniform")
        {
            UniformMeshSchema(coordSet);
            break;
        }
        else if (coordSetType == "rectilinear")
        {
            RectilinearMeshSchema(coordSet);
            break;
        }
        else if (coordSetType == "explicit")
        {
            ExplicitMeshSchema(coordSet, topoSet);
            explicitMesh = true;
            break;
        }
        else
        {
            cout<<"***************************************"<<endl;
            cout<<"*****WARNING: meshType("<<coordSetType<<") not yet supported"<<endl;
        }
    }

    if (child_domain.has_child("fields"))
    {
        // if we don't specify a topology, find the first topology ...
        NodeConstIterator itr = child_domain["topologies"].children();
        itr.next();
        std::string  topo_name = itr.name();

        // as long as mesh blueprint verify true, we access data without fear.
        const Node &n_topo   = child_domain["topologies"][topo_name];
        const Node &fields = child_domain["fields"];
        NodeConstIterator fields_itr = fields.children();

        while(fields_itr.has_next())
        {
            const Node& field = fields_itr.next();
            std::string field_name = fields_itr.name();
            bool saveField = (variables.empty() ? true : false);
            //cerr << "seeing if we want to save: " << field_name << endl;
            for (auto &v : variables)
                if (field_name == v)
                {
                    saveField = true;
                    break;
                }

            if (saveField)
                FieldVariable(field_name, field, n_topo);
        }
    }
//cerr << " " << rank << " finished saving vars " << endl;
//MPI_Barrier(mpi_comm);
//cerr << "Ascent finished adios send" << endl;
//MPI_Barrier(mpi_comm);
//cerr << __FILE__ << " " << __LINE__ << endl;
//MPI_Barrier(mpi_comm);
    adios_close(adiosFile);
//MPI_Barrier(mpi_comm);
    //adios_advance_step(adiosFile, 0, 1000);
    step++;
//MPI_Barrier(mpi_comm);
//cerr << __FILE__ << " " << __LINE__ << endl;
}

//-----------------------------------------------------------------------------
bool
ADIOS::UniformMeshSchema(const Node &node)
{
    if (rank == 0)
    {
        cout<<"***************************************"<<endl;
        cout<<"*****WARNING: ADIOS Uniform mesh schema not yet supported "<<endl;
    }
    return false;
}


//-----------------------------------------------------------------------------
bool
ADIOS::CalcExplicitMeshInfo(const conduit::Node &node, 
                            const conduit::Node &topoNode, 
                            vector<vector<double>> &XYZ, 
                            vector<int> &topoConnectivity)
{
    const Node &X = node["x"];
    const Node &Y = node["y"];
    const Node &Z = node["z"];

    const double *xyzPtr[3] = {X.as_float64_ptr(),
                               Y.as_float64_ptr(),
                               Z.as_float64_ptr()};

    localDims = {X.dtype().number_of_elements(),
                 Y.dtype().number_of_elements(),
                 Z.dtype().number_of_elements(),
                 0};

    const Node &con = topoNode["elements/connectivity"];

   /* cout<<"***************************************"<<endl;
    cout<<"*****x size: "<<X.dtype().number_of_elements()<<endl;
    cout<<"*****y size: "<<Y.dtype().number_of_elements()<<endl;
    cout<<"*****z size: "<<Z.dtype().number_of_elements()<<endl;
    cout<<"*****con size: "<<con.dtype().number_of_elements()<<endl; 
*/
    //Stuff the XYZ coordinates into the conveniently provided array.
    XYZ.resize(3);
    for (int i = 0; i < 3; i++)
    {
        XYZ[i].resize(localDims[i]);
        std::memcpy(&(XYZ[i][0]), xyzPtr[i], localDims[i]*sizeof(double));
    }


//cerr << "!!!!!!!! detailed topo" << endl;    
//topoNode.print_detailed();
    
    localDimsCon = {con.dtype().number_of_elements()};
    const int *conPtr = con.as_int32_ptr();
    for(int z = 0; z < con.dtype().number_of_elements(); z++)
    {
        topoConnectivity.push_back(conPtr[z]);
    }    

    //Participation trophy if you only bring 1 rank to the game.
    if (numRanks == 1)
    {
        offset = {0,0,0};
        globalDims = localDims;
        offsetCon = {0};
        globalDimsCon = localDimsCon;
        return true;
    }

#ifdef ASCENT_MPI_ENABLED

    // Have to figure out the indexing for each rank.
    vector<int> ldims(3*numRanks, 0); //, buff(3*numRanks,0);
    ldims[3*rank + 0] = localDims[0];
    ldims[3*rank + 1] = localDims[1];
    ldims[3*rank + 2] = localDims[2];

    //int mpiStatus;
    //mpiStatus = MPI_Allreduce(&ldims[0], &buff[0], ldims.size(), MPI_INT, MPI_SUM, mpi_comm);
    //if (mpiStatus != MPI_SUCCESS)
    //    return false;

    //Calculate the global dims. This is just the sum of all the localDims.
    globalDims = {localDims[0],localDims[1],localDims[2]};
#if 0
    globalDims = {numRanks,0,0,0};
    for (int i = 0; i < buff.size(); i+=3)
    {
        globalDims[1] += buff[i + 0];
        globalDims[2] += buff[i + 1];
        globalDims[3] += buff[i + 2];
    }
#endif

    //And now for the offsets. It is the sum of all the localDims before me.
    offset = {0,0,0};
    /*
    for (int i = 0; i < rank; i++)
    {
        offset[0] += buff[i*3 + 0];
        offset[1] += buff[i*3 + 1];
        offset[2] += buff[i*3 + 2];
    }
    */

#if 0
    if (rank == 0)
    {
        cout<<"***************************************"<<endl;
        cout<<"*****globalDims: "<<globalDims<<endl;
    }
    MPI_Barrier(mpi_comm);
    for (int i = 0; i < numRanks; i++)
    {
        if (i == rank)
        {
            cout<<"  "<<rank<<": *****localDims:"<<localDims<<endl;
            cout<<"  "<<rank<<": *****offset:"<<offset<<endl;
            cout<<"  X: "<<rank<<XYZ[0]<<endl;
            cout<<"  Y: "<<rank<<XYZ[1]<<endl;
            cout<<"  Z: "<<rank<<XYZ[2]<<endl;
            cout<<"***************************************"<<endl<<endl;
        }
        MPI_Barrier(mpi_comm);
    }
#endif

/*
    // Have to figure out the indexing for each rank.
    vector<int> ldims(3*numRanks, 0), buff(3*numRanks,0);
    ldims[3*rank + 0] = localDims[0];
    ldims[3*rank + 1] = localDims[1];
    ldims[3*rank + 2] = localDims[2];

    int mpiStatus;
    mpiStatus = MPI_Allreduce(&ldims[0], &buff[0], ldims.size(), MPI_INT, MPI_SUM, mpi_comm);
    if (mpiStatus != MPI_SUCCESS)
        return false;

    //Calculate the global dims. This is just the sum of all the localDims.
    globalDims = {0,0,0};
    for (int i = 0; i < buff.size(); i+=3)
    {
        globalDims[0] += buff[i + 0];
        globalDims[1] += buff[i + 1];
        globalDims[2] += buff[i + 2];
    }

    //And now for the offsets. It is the sum of all the localDims before me.
    offset[0] = 0; //with more than one rank, this has to be reset to 0 now
    for (int i = 0; i < rank; i++)
    {
        offset[0] += buff[i*3 + 0];
        offset[1] += buff[i*3 + 1];
        offset[2] += buff[i*3 + 2];
    }
*/

    //Calculate the global dims. This is just the sum of all the localDims.
    globalDimsCon = {localDimsCon[0]};

    //And now for the offsets. It is the sum of all the localDims before me.
    offsetCon = {0}; //with more than one rank, this has to be reset to 0 now

    return true;
#endif
}


//-----------------------------------------------------------------------------
bool
ADIOS::ExplicitMeshSchema(const Node &node, const Node &topoNode)
{
    //ensure that the coordinates are valid
    if (!node.has_child("values"))
        return false;

    const Node &coords = node["values"];
    if (!coords.has_child("x") || !coords.has_child("y") || !coords.has_child("z"))
        return false;

    vector<vector<double>> XYZ;
    vector<int> topoConnectivity;
    if (!CalcExplicitMeshInfo(coords, topoNode, XYZ, topoConnectivity))
        return false;

    string coordNames[3] = {"coords_x", "coords_y", "coords_z"};

    //Write schema metadata for Expl. Mesh.
    if (rank == 0)
    {
        //cout<<"**************************************************"<<endl;
        //cout<<rank<<": globalDims: "<<dimsToStr(globalDims)<<endl;
        //cout<<rank<<": localDims: "<<dimsToStr(localDims)<<endl;
        //cout<<rank<<": offset: "<<dimsToStr(offset)<<endl;

        //indicate this is an unstructured mesh, let reader figure out how to read it
        adios_define_mesh_unstructured(0, 0, 0, 0, 0, 0, adiosGroup, meshName.c_str());
    }

    //Write out coordinates.
    int64_t ids[3];
    for (int i = 0; i < 3; i++)
    {
        //local dimensions
        vector<int64_t> l = {1,localDims[i]};
        //global dimensions
        vector<int64_t> g = {numRanks,globalDims[i]};
        //offsets
        vector<int64_t> o = {rank,offset[i]};
        ids[i] = adios_define_var(adiosGroup,
                                  coordNames[i].c_str(),
                                  "",
                                  adios_double,
                                  dimsToStr(l).c_str(),
                                  dimsToStr(g).c_str(),
                                  dimsToStr(o).c_str());

                                  /*
                                  to_string(localDims[1+i]).c_str(),
                                  to_string(globalDims[1+i]).c_str(),
                                  to_string(offset[1+i]).c_str());
                                  */
        adios_write_byid(adiosFile, ids[i], (void *)&(XYZ[i][0]));
    }


    //write out the connectivity
    int64_t idsCon[1];
    //local dimensions
    vector<int64_t> lCon = {1,localDimsCon[0]};
    //global dimensions
    vector<int64_t> gCon = {numRanks,globalDimsCon[0]};
    //offsets
    vector<int64_t> oCon = {rank,offsetCon[0]};
    idsCon[0] = adios_define_var(adiosGroup,
                              "connectivity",
                              "",
                              adios_integer,
                              dimsToStr(lCon).c_str(),
                              dimsToStr(gCon).c_str(),
                              dimsToStr(oCon).c_str());
    adios_write_byid(adiosFile, idsCon[0], (void *)&(topoConnectivity[0]));

    return true;
}


//-----------------------------------------------------------------------------
bool
ADIOS::CalcRectilinearMeshInfo(const conduit::Node &node,
                               vector<vector<double>> &XYZ)
{
    const Node &X = node["x"];
    const Node &Y = node["y"];
    const Node &Z = node["z"];

    const double *xyzPtr[3] = {X.as_float64_ptr(),
                               Y.as_float64_ptr(),
                               Z.as_float64_ptr()};

    localDims = {1,
                 X.dtype().number_of_elements(),
                 Y.dtype().number_of_elements(),
                 Z.dtype().number_of_elements()};

    //Stuff the XYZ coordinates into the conveniently provided array.
    XYZ.resize(3);
    for (int i = 0; i < 3; i++)
    {
        XYZ[i].resize(localDims[i+1]);
        std::memcpy(&(XYZ[i][0]), xyzPtr[i], localDims[i+1]*sizeof(double));
    }

    //Participation trophy if you only bring 1 rank to the game.
    if (numRanks == 1)
    {
        offset = {0,0,0};
        globalDims = localDims;
        return true;
    }

#ifdef ASCENT_MPI_ENABLED

    // Have to figure out the indexing for each rank.
    vector<int> ldims(3*numRanks, 0); //, buff(3*numRanks,0);
    ldims[3*rank + 0] = localDims[0];
    ldims[3*rank + 1] = localDims[1];
    ldims[3*rank + 2] = localDims[2];

    //int mpiStatus;
    //mpiStatus = MPI_Allreduce(&ldims[0], &buff[0], ldims.size(), MPI_INT, MPI_SUM, mpi_comm);
    //if (mpiStatus != MPI_SUCCESS)
    //    return false;

    //Calculate the global dims. This is just the sum of all the localDims.
    globalDims = {numRanks,localDims[1],localDims[2],localDims[3]};
#if 0
    globalDims = {numRanks,0,0,0};
    for (int i = 0; i < buff.size(); i+=3)
    {
        globalDims[1] += buff[i + 0];
        globalDims[2] += buff[i + 1];
        globalDims[3] += buff[i + 2];
    }
#endif

    //And now for the offsets. It is the sum of all the localDims before me.
    offset = {rank,0,0,0};
    /*
    for (int i = 0; i < rank; i++)
    {
        offset[0] += buff[i*3 + 0];
        offset[1] += buff[i*3 + 1];
        offset[2] += buff[i*3 + 2];
    }
    */

#if 0
    if (rank == 0)
    {
        cout<<"***************************************"<<endl;
        cout<<"*****globalDims: "<<globalDims<<endl;
    }
    MPI_Barrier(mpi_comm);
    for (int i = 0; i < numRanks; i++)
    {
        if (i == rank)
        {
            cout<<"  "<<rank<<": *****localDims:"<<localDims<<endl;
            cout<<"  "<<rank<<": *****offset:"<<offset<<endl;
            cout<<"  X: "<<rank<<XYZ[0]<<endl;
            cout<<"  Y: "<<rank<<XYZ[1]<<endl;
            cout<<"  Z: "<<rank<<XYZ[2]<<endl;
            cout<<"***************************************"<<endl<<endl;
        }
        MPI_Barrier(mpi_comm);
    }
#endif

    return true;

#endif
}


//-----------------------------------------------------------------------------
bool
ADIOS::RectilinearMeshSchema(const Node &node)
{
    if (!node.has_child("values"))
        return false;

    const Node &coords = node["values"];
    if (!coords.has_child("x") || !coords.has_child("y") || !coords.has_child("z"))
        return false;

    vector<vector<double>> XYZ;
    if (!CalcRectilinearMeshInfo(coords, XYZ))
        return false;

    string coordNames[3] = {"coords_x", "coords_y", "coords_z"};

    //Write schema metadata for Rect Mesh.
    if (rank == 0)
    {
        
        cout<<"**************************************************"<<endl;
        cout<<rank<<": globalDims: "<<dimsToStr(globalDims)<<endl;
        cout<<rank<<": localDims: "<<dimsToStr(localDims)<<endl;
        cout<<rank<<": offset: "<<dimsToStr(offset)<<endl;
        

        //adios_define_mesh_timevarying("no", adiosGroup, meshName.c_str());
        adios_define_mesh_rectilinear((char*)dimsToStr(globalDims).c_str(),
                                      (char*)(coordNames[0]+","+coordNames[1]+","+coordNames[2]).c_str(),
                                      0,
                                      adiosGroup,
                                      meshName.c_str());
    }

    //Write out coordinates.
    int64_t ids[3];
    for (int i = 0; i < 3; i++)
    {
        vector<int64_t> l = {1,localDims[i+1]};
        vector<int64_t> g = {numRanks,globalDims[i+1]};
        vector<int64_t> o = {rank,offset[i+1]};
        ids[i] = adios_define_var(adiosGroup,
                                  coordNames[i].c_str(),
                                  "",
                                  adios_double,
                                  dimsToStr(l).c_str(),
                                  dimsToStr(g).c_str(),
                                  dimsToStr(o).c_str());

                                  /*
                                  to_string(localDims[1+i]).c_str(),
                                  to_string(globalDims[1+i]).c_str(),
                                  to_string(offset[1+i]).c_str());
                                  */
        adios_write_byid(adiosFile, ids[i], (void *)&(XYZ[i][0]));
    }

    return true;
}

//-----------------------------------------------------------------------------
bool
ADIOS::FieldVariable(const string &fieldName, const Node &node, const Node &n_topo)
{
    // TODO: we can assume this is true if verify is true and this is a rect mesh.
    if (!node.has_child("values") ||
        !node.has_child("association") //||
        //!node.has_child("type")
       )
    {
        cerr << "Field Variable not supported at this time" << endl;
        return false;
    }

//    const string &fieldType = node["type"].as_string();
    const string &fieldAssoc = node["association"].as_string();


/*    if (fieldType != "scalar")
    {
        ASCENT_INFO("Field type "
                    << fieldType
                    << " not supported for ADIOS this time");
        cerr << "Field type " << fieldType << " not supported for ADIOS at this time";
        return false;
    }*/
    if (fieldAssoc != "vertex" && fieldAssoc != "element")
    {
        ASCENT_INFO("Field association "
                    << fieldAssoc
                    <<" not supported for ADIOS this time");
        cerr << "Field association " << fieldAssoc << " not supported for ADIOS at this time";
        return false;
    }

//    if(node["values"].number_of_children() == 1)
 //   {

        //!!This is only good when one variable is passed to adios
        //its a vector
        //node["values"].number_of_children()
        const Node &field_values = node["values"];
        //field_values.schema().print();
        const double *vals = field_values.as_double_ptr();

        /*
        cerr << "assoc: " << fieldAssoc << endl;
        node.print_detailed();
        cout<<"FIELD "<<fieldName<<" #= "<<field_values.dtype().number_of_elements()<<endl;
        cout<<"localDims: "<<dimsToStr(localDims, (fieldAssoc=="vertex"), explicitMesh)<<endl;
        cout<<"globalDims: "<<dimsToStr(globalDims, (fieldAssoc=="vertex"), explicitMesh)<<endl;
        cout<<"offset: "<<dimsToStr(offset, (fieldAssoc=="vertex"), explicitMesh)<<endl;
        */

        if(!explicitMesh)
        {
            int64_t varId = adios_define_var(adiosGroup,
                                             (char*)fieldName.c_str(),
                                             "",
                                             adios_double,
                                             dimsToStr(localDims, (fieldAssoc=="vertex")).c_str(),
                                             dimsToStr(globalDims, (fieldAssoc=="vertex")).c_str(),
                                             dimsToStr(offset, (fieldAssoc=="vertex")).c_str());
            adios_define_var_mesh(adiosGroup,
                                  (char*)fieldName.c_str(),
                                  meshName.c_str());
            adios_define_var_centering(adiosGroup,
                                       fieldName.c_str(),
                                       (fieldAssoc == "vertex" ? "point" : "cell"));
            adios_write(adiosFile, fieldName.c_str(), (void*)vals);
        }
        else //need to write seperate array for each cell type
        {
            string mesh_type     = n_topo["type"].as_string();

            //hack for a single cell type for unstructured
            if(mesh_type == "unstructured") //assuming we have a cube here, needs expanded for zoo
            {
                int numElements = field_values.dtype().number_of_elements();

                //local dimensions
                vector<int64_t> l = {1,numElements};
                //global dimensions
                vector<int64_t> g = {numRanks,numElements};
                //offsets
                vector<int64_t> o = {rank,0};
          

                //write the field data
                int64_t varId = adios_define_var(adiosGroup,
                                             (char*)fieldName.c_str(),
                                             "",
                                             adios_double,
                                             dimsToStr(l, (fieldAssoc=="vertex"), explicitMesh).c_str(),
                                             dimsToStr(g, (fieldAssoc=="vertex"), explicitMesh).c_str(),
                                             dimsToStr(o, (fieldAssoc=="vertex"), explicitMesh).c_str());
                adios_define_var_mesh(adiosGroup,
                                      (char*)fieldName.c_str(),
                                      meshName.c_str());
                adios_define_var_centering(adiosGroup,
                                           fieldName.c_str(),
                                           (fieldAssoc == "vertex" ? "point" : "cell"));
                adios_write(adiosFile, fieldName.c_str(), (void*)vals);

                //write the offset data for the field
            }
            else if(mesh_type =="unstructured")
            {
                cerr << "This is a bad place to be" << endl;
            }
      }
/*    }
    else
    {
        const vector<string> nodeVals = {"values/v0", "values/v1", "values/v2"};
        const vector<string> names = {"velocity_x", "velocity_y", "velocity_z"};
        
        for(int z = 0; z < 3; z++)
        {
            const Node &field_values = node[nodeVals[z]];
            //field_values.schema().print();
            const double *vals = field_values.as_double_ptr();
     
            cerr << "we are a vector -- assoc: " << fieldAssoc << endl;
            node.print_detailed();
            cout<<"FIELD "<<fieldName<<" #= "<<field_values.dtype().number_of_elements()<<endl;
            cout<<"localDims: "<<dimsToStr(localDims, (fieldAssoc=="vertex"), explicitMesh)<<endl;
            cout<<"globalDims: "<<dimsToStr(globalDims, (fieldAssoc=="vertex"), explicitMesh)<<endl;
            cout<<"offset: "<<dimsToStr(offset, (fieldAssoc=="vertex"), explicitMesh)<<endl;
       
            string mesh_type     = n_topo["type"].as_string();
            //hack for a single cell type for unstructured
            if(mesh_type == "unstructured") //assuming we have a cube here, needs expanded for zoo
            {
                int numElements = field_values.dtype().number_of_elements();

                //local dimensions
                vector<int64_t> l = {1,numElements};
                //global dimensions
                vector<int64_t> g = {numRanks,numElements};
                //offsets
                vector<int64_t> o = {rank,0};
          

                //write the field data
                int64_t varId = adios_define_var(adiosGroup,
                                             (char*)names[z].c_str(),
                                             "",
                                             adios_double,
                                             dimsToStr(l, (fieldAssoc=="vertex"), explicitMesh).c_str(),
                                             dimsToStr(g, (fieldAssoc=="vertex"), explicitMesh).c_str(),
                                             dimsToStr(o, (fieldAssoc=="vertex"), explicitMesh).c_str());
                adios_define_var_mesh(adiosGroup,
                                      (char*)names[z].c_str(),
                                      meshName.c_str());
                adios_define_var_centering(adiosGroup,
                                           names[z].c_str(),
                                           (fieldAssoc == "vertex" ? "point" : "cell"));
                adios_write(adiosFile, names[z].c_str(), (void*)vals);

                //write the offset data for the field
            }
        }
    }*/
    return true;
}

//-----------------------------------------------------------------------------
};
//-----------------------------------------------------------------------------
// -- end ascent::runtime::filters --
//-----------------------------------------------------------------------------


//-----------------------------------------------------------------------------
};
//-----------------------------------------------------------------------------
// -- end ascent::runtime --
//-----------------------------------------------------------------------------


//-----------------------------------------------------------------------------
};
//-----------------------------------------------------------------------------
// -- end ascent:: --
//-----------------------------------------------------------------------------
