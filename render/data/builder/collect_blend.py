
import argparse
import io
import math
import os
import sys
import zipfile
from collections import defaultdict

import bpy

from utils.config import Config

if Config.misc.blender_silent:
    import bpy_extras.wm_utils.progress_report
    import io_scene_obj.import_obj

    bpy_extras.wm_utils.progress_report.print = lambda t, *args, **kwargs : None
    io_scene_obj.import_obj.print = lambda t : None if t.startswith("\tMaterial not found MTL: ") else print(t)

from utils.io import read_serialized
from utils.io import write_serialized
from utils.shape_net import  SHAPE_NET_CATEGORY
from utils.shape_net import  SHAPE_NET_NUMS
from utils.pool import pool_map


SHARED_ZIP_FILE: zipfile.ZipFile = ...
SHARED_ZIP_SEEK = 0
SHARED_ZIP_DICT = {}


def setup_shared_zip_file():
    global SHARED_ZIP_FILE
    global SHARED_ZIP_SEEK
    global SHARED_ZIP_DICT

    SHARED_ZIP_FILE = zipfile.ZipFile(Config.data.shape_net_zip, "r")

    object_paths = sorted(
        p for p in SHARED_ZIP_FILE.namelist() if p.endswith("/model_normalized.obj")
    )
    category_map = defaultdict(lambda: "{:04d}".format(len(category_map)))
    shape_id_map = defaultdict(lambda: "{:06d}".format(len(shape_id_map)))

    for path in object_paths:
        splits = path.split("/")
        category = category_map[splits[1]]
        shape_id = shape_id_map[splits[1], splits[2]]
        SHARED_ZIP_DICT[category, shape_id] = path

    SHARED_ZIP_SEEK = SHARED_ZIP_FILE.fp.tell()


def fixup_shared_zip_file():
    SHARED_ZIP_FILE.fp = io.open(Config.data.shape_net_zip, "rb")
    SHARED_ZIP_FILE.fp.seek(SHARED_ZIP_SEEK)


def setup_empty_home_file():
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.data.scenes[0].view_settings.view_transform = "Standard"
    bpy.ops.wm.save_homefile()


def parse_args():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("--start_index", help="image index to start", type=int)
    parser.add_argument("--stride", help="image index stride", type=int, default=1)
    parser.add_argument("--reduce", help="reduce all results", type=int, default=0)
    return parser.parse_args()


def obj_to_blend(cat_name, shape_name):
    name = cat_name + shape_name
    out_path = os.path.join(Config.data.shape_net_dir, cat_name, shape_name + ".blend")

    if os.path.exists(out_path):
        bpy.ops.wm.open_mainfile(filepath=out_path)
        object = bpy.context.view_layer.objects.active = bpy.context.scene.objects[0]
        return (
            name,
            tuple(x / 2 for x in object.dimensions),
        )

    zip_path = SHARED_ZIP_DICT[cat_name,shape_name]
    obj_path = os.path.join(Config.data.shape_net_tmp, zip_path)
    SHARED_ZIP_FILE.extract(zip_path, Config.data.shape_net_tmp)

    sys.stdout.flush()

    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.ops.import_scene.obj(filepath=obj_path, split_mode="OFF")

    os.unlink(obj_path)

    object = bpy.context.view_layer.objects.active = bpy.context.scene.objects[0]
    object.name = name

    # setting the centre to the center of bounding box
    max_dimension = max(object.dimensions)
    scaling = 2.0 / max_dimension
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.transform.translate(value=[0, 0, 0])
    bpy.ops.transform.rotate(value=-math.pi / 2, orient_axis="X")
    bpy.ops.transform.resize(value=[scaling, scaling, scaling])
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    for ob in bpy.context.editable_objects:
        for i in range(len(ob.material_slots)-1, -1, -1):
            ob.active_material_index = i
            bpy.ops.object.material_slot_remove()

    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)

    bpy.ops.wm.save_as_mainfile(filepath=out_path, compress=Config.misc.blender_packed)

    sys.stdout.flush()

    return (
        name,
        tuple(x / 2 for x in object.dimensions),
    )



if __name__ == "__main__":
    #   args = parse_args()
    #   if args.start_index is None:
    #       args.start_index = get_host_id() % args.stride

    args_start_index = 0
    args_stride = 1
    args_reduce = "--reduce" in sys.argv

    if not args_reduce:
        setup_empty_home_file()
        setup_shared_zip_file()

        worker_args = []

        os.makedirs(Config.data.shape_net_tmp, exist_ok=True)

        for cat_id in SHAPE_NET_CATEGORY.keys():
            os.makedirs(os.path.join(Config.data.shape_net_dir, cat_id), exist_ok=True)

            for shape_id in range(SHAPE_NET_NUMS[cat_id]):
                shape_id = "{:06d}".format(shape_id)
                worker_args.append((cat_id, shape_id))

        worker_args.sort()
        worker_args = worker_args[args_start_index::args_stride]

        all_dimensions = pool_map(
            obj_to_blend,
            worker_args,
            Config.data.shape_net_cpu,
            initializer=fixup_shared_zip_file,
        )

        write_serialized(
            dict(all_dimensions),
            os.path.join(Config.data.shape_net_dir, "all_dimensions_{:02d}.json".format(args_start_index)),
        )

    if args_reduce or args_stride == 1:
        all_dimensions = {}
        for i in range(args_stride):
            all_dimensions.update(read_serialized(
                os.path.join(Config.data.shape_net_dir, "all_dimensions_{:02d}.json".format(i)),
            ))

        write_serialized(
            dict(all_dimensions),
            os.path.join(Config.data.shape_net_dir, "all_dimensions.json"),
        )

        to_rotate_index = defaultdict(int)
        for name, dimension in all_dimensions.items():
            # x > y bad
            if dimension[0] > dimension[1]:
                to_rotate_index[name[:4]] += 1
            else:
                to_rotate_index[name[:4]] -= 1

        write_serialized(
            dict(to_rotate_index),
             os.path.join(Config.data.shape_net_dir, "categories_to_rotate.json"),
        )
