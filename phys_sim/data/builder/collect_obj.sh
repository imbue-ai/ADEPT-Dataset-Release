#!/usr/bin/env bash

set -e
set -u

if [[ "$#" != "1" ]]
then
    echo "the first argument needs to be a path to the ShapeNet directory"
    echo "(no path provided)"
    exit 1
fi

if [[ ! -f "$1/taxonomy.json" ]]
then
    echo "the first argument needs to be a path to the ShapeNet directory"
    echo "$1/taxonomy.json does not exist"
    exit 2
fi


shape_net_folder=$(readlink -f "$1")
collect_script_dir=$(dirname "$0")
sim_object_folder=$(readlink -f "${collect_script_dir}/../additional_shapes")


shape_total=0
cat_count=0
for cat_folder in ${shape_net_folder}/*
do
    cat_count_4=000${cat_count}
    cat_count_4=${cat_count_4:(-4)}
    mkdir -p ${sim_object_folder}/${cat_count_4}
    shape_count=0
    for obj_folder in ${cat_folder}/*
    do
        model_file=${obj_folder}/models/model_normalized.obj
        if [[ -e ${model_file} ]]
        then
            shape_count_6=00000${shape_count}
            shape_count_6=${shape_count_6:(-6)}
            shape_file=${sim_object_folder}/${cat_count_4}/${shape_count_6}.obj
            ln -s ${model_file} ${shape_file}
            shape_count=$(($shape_count+1))
        fi
    done
    echo ${cat_count_4}
    cat_count=$((cat_count+1))
    shape_total=$((shape_total+shape_count))
done

echo "${shape_total} files linked"
