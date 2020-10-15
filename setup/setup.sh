#!/bin/bash

set -e
set -u

# a directory where ShapeNetCore.v2.zip is, will download if needed, and unpack there
SHAPE_DATA_DIR=/media/bawr/ev850/data/ShapeNetCore.v2
CONDA_ENV_NAME=ADEPT

ARIA2_NSTREAMS=8

SHAPE_NET_ROOT=http://shapenet.cs.stanford.edu/shapenet/obj-zip
SHAPE_ZIP_SIZE=52472
SHAPE_ZIP_ROOT=ShapeNetCore.v2
SHAPE_ZIP_FILE=ShapeNetCore.v2.zip
SHAPE_CHECKSUM=ShapeNetCore.v2.zip.md5


mkdir -p  ${SHAPE_DATA_DIR}
pushd     ${SHAPE_DATA_DIR}

aria2c -c ${SHAPE_NET_ROOT}/${SHAPE_ZIP_FILE} -s ${ARIA2_NSTREAMS} -x ${ARIA2_NSTREAMS}
aria2c -c ${SHAPE_NET_ROOT}/${SHAPE_CHECKSUM}

echo

if [ ! -e ${SHAPE_DATA_DIR}/${SHAPE_ZIP_ROOT}/taxonomy.json ]
then
unzip -ou ${SHAPE_ZIP_FILE} '*/*/*/models/model_normalized.obj' '*/taxonomy.json' | pv -l -s ${SHAPE_ZIP_SIZE} | wc -l
fi

echo

popd

conda env create --force --file ${0%.sh}.yaml --name ${CONDA_ENV_NAME}

echo
echo "next steps (put them somewhere safe):"
echo '$ '"touch ./phys_sim/data/additional_shapes/.pretend_we_extracted_stuff"
#### '$ '"./phys_sim/data/builder/collect_obj.sh ${SHAPE_DATA_DIR}/${SHAPE_ZIP_ROOT}"
echo '$ '"conda activate ${CONDA_ENV_NAME}"
echo '$ time PYTHONPATH=. python3 ./render/data/builder/collect_blend.py'
echo
