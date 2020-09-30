import argparse
from multiprocessing import Pool, cpu_count
import os
import sys
from collections import defaultdict

import numpy as np
import bpy

from utils.io import write_serialized, read_serialized
from utils.misc import get_host_id
from utils.shape_net import SIM_SHAPE_NET_FOLDER, RENDER_SHAPE_NET_FOLDER, SHAPE_NET_CATEGORY, SHAPE_NET_NUMS, mkdir


def parse_args():
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('--start_index', help='image index to start', type=int)
    parser.add_argument("--stride", help="image index stride", type=int, default=1)
    parser.add_argument("--reduce", help="reduce all results", type=int, default=0)
    return parser.parse_args()


def prepare_empty_scene_and_fix_filmic_complaints():
    bpy.ops.wm.read_homefile(use_empty=True)
    bpy.data.scenes[0].view_settings.view_transform = 'Standard'
    bpy.ops.wm.save_homefile()


def obj_to_blend(cat_name, shape_name):
    name = cat_name + shape_name
    file_path = os.path.join(SIM_SHAPE_NET_FOLDER, cat_name, "{}.obj".format(shape_name))
    out_path = os.path.join(RENDER_SHAPE_NET_FOLDER, cat_name, "{}.blend".format(shape_name))

    os.makedirs(os.path.join(RENDER_SHAPE_NET_FOLDER, cat_name), exist_ok=True)
    bpy.ops.wm.read_homefile(use_empty=True)
    # bpy.ops.object.select_all(action='SELECT')
    # bpy.ops.object.delete()

    try:
        bpy.ops.import_scene.obj(filepath=file_path, split_mode="OFF")
    except:
        sys.stderr.write("ERROR: {}\n".format(file_path))
        sys.stderr.flush()
        return (name, None)

    object = bpy.context.view_layer.objects.active = bpy.context.scene.objects[0]
    object.name = name

    # setting the centre to the center of bounding box
    max_dimension = max(object.dimensions)
    scaling = 2. / max_dimension

    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

    # object.mesh.double_sided = True
    # supposedly this is the default?
    # see:
    # https://blender.stackexchange.com/questions/108045/how-to-enable-double-sided-normals-or-double-sided-faces-for-rendering-in-python
    # https://github.com/KhronosGroup/glTF-Blender-Exporter/issues/58
    # https://devtalk.blender.org/t/where-did-double-sided-normals-disappeared/7586

    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.transform.translate(value=[0, 0, 0])
    bpy.ops.transform.rotate(value=-np.pi / 2, orient_axis="X")  # not sure for axis
    bpy.ops.transform.resize(value=[scaling, scaling, scaling])
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    # remove all materials EXCEPT FUCKING PROPERLY AND WITHOUT BLENDER CRASHES
    for ob in bpy.context.editable_objects:
        for i in reversed(range(len(ob.material_slots))):
            ob.active_material_index = i
            bpy.ops.object.material_slot_remove()

    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)

    sys.stdout.write("{} generated\n".format(name))
    bpy.ops.wm.save_as_mainfile(filepath=out_path)
    sys.stdout.write("{} collected\n".format(name))
    sys.stdout.flush()

    return (name, tuple(x / 2 for x in object.dimensions))



if __name__ == '__main__':
    args = parse_args()
    if args.start_index is None:
        args.start_index = get_host_id() % args.stride

    prepare_empty_scene_and_fix_filmic_complaints()

    if args.reduce:
        all_dimensions = dict()
        for i in range(args.stride):
            all_dimensions.update(
                read_serialized(os.path.join(SIM_SHAPE_NET_FOLDER, "all_dimensions_{:02d}.json".format(i))))

        write_serialized(dict(all_dimensions),
                         os.path.join(SIM_SHAPE_NET_FOLDER, "all_dimensions.json"))

        to_rotate_index = defaultdict(int)
        for name, dimension in all_dimensions.items():
            # x > y bad
            if dimension[0] > dimension[1]:
                to_rotate_index[name[:4]] += 1
            else:
                to_rotate_index[name[:4]] -= 1
        write_serialized(dict(to_rotate_index),
                         os.path.join(SIM_SHAPE_NET_FOLDER, "categories_to_rotate.json"))

    else:
        worker_args = []

        for cat_id in SHAPE_NET_CATEGORY.keys():
            for shape_id in range(SHAPE_NET_NUMS[cat_id]):
                shape_id = "{:06d}".format(shape_id)
                worker_args.append((cat_id, shape_id))

        worker_args.sort()
        worker_args = worker_args[args.start_index::args.stride]

        with Pool(cpu_count()) as p:
            # TODO: this *really* should be using unordered_imap and/or a chunksize of 16
            # right now even if you have 10+ cores, only 1 will be used for the most part
            # since the task complexity is uneven and most of the workers finish early :(
            # TODO: actually switching it over from starmap causes the workers to hang :(
            # I suspect it's some cursed Blender interaction, but I can't reproduce it :(
            all_dimensions = p.starmap(obj_to_blend, worker_args, 16)
            print("starmap done")

        write_serialized(dict(all_dimensions),
                         os.path.join(SIM_SHAPE_NET_FOLDER, "all_dimensions_{:02d}.json".format(args.start_index)))


# 0053000963 generated
# 0053000963 collected
