#!/bin/bash

set -e
set -u

export BLENDERBIN=/home/bawr/Projects/Blender/build_linux_headless/bin/blender
export PYTHONPATH=${CONDA_PREFIX}/lib/python3.7/site-packages:.

rm -f ./blender.*
rm -f ./collect.*
rm -f ./workers.*

echo > /tmp/blender.crash.txt

time ${BLENDERBIN} --python-use-system-env --python ./render/data/builder/collect_blend.py 1> collect.log 2> collect.err

# PYTHONPATH=. python3 ./render/data/builder/collect_blend.py 1> collect.log 2> collect.err
