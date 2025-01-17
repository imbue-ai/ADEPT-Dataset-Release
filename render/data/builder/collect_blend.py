
import argparse
import datetime
from multiprocessing import Pool, cpu_count
import os
import sys
import zipfile
import tempfile
from collections import defaultdict

import math
import bpy

FAST=10
DIRECT_ZIP=True

# noinspection PyUnresolvedReferences
import bpy_extras.wm_utils.progress_report
# noinspection PyUnresolvedReferences
import io_scene_obj.import_obj

if FAST:
    bpy_extras.wm_utils.progress_report.print = lambda t, *args, **kwargs : None
    io_scene_obj.import_obj.print = lambda t : None if t.startswith("\tMaterial not found MTL: ") else print(t)

from utils.io import write_serialized, read_serialized
from utils.misc import get_host_id
from utils.shape_net import SIM_SHAPE_NET_FOLDER, RENDER_SHAPE_NET_FOLDER, SHAPE_NET_CATEGORY, SHAPE_NET_NUMS, mkdir


if DIRECT_ZIP:
    print("ZIP MAGIC YAAAAAAAAY")
    DIRECT_ZIP_TEMP_DIR = "/dev/shm/blend"
    os.makedirs(DIRECT_ZIP_TEMP_DIR, exist_ok=True)

    # want a global zip file / contents accessible by qall the workers
    ZIP_PATH = "/media/bawr/ev850/data/ShapeNetCore.v2/ShapeNetCore.v2.zip"
    DIRECT_ZIP_FILE = zipfile.ZipFile(ZIP_PATH, "r")
    normalized_objs = [t for t in DIRECT_ZIP_FILE.namelist() if "model_normalized.obj" in t]
    shapes = defaultdict(lambda: len(shapes))
    categories = defaultdict(lambda: len(categories))
    DIRECT_ZIP_MAP = {}
    for path in sorted(normalized_objs):
        splits = path.split('/')
        category_number = splits[1]
        shape_number = splits[2]
        DIRECT_ZIP_MAP[f"{categories[category_number]:04}/{shapes[shape_number]:06}"] = path
    ZIP_FILE_POSITION = DIRECT_ZIP_FILE.fp.tell()


def maybe_fix_zip_file():
    if DIRECT_ZIP:
        import threading
        import io
        DIRECT_ZIP_FILE.fp = io.open(ZIP_PATH, "rb")
        DIRECT_ZIP_FILE.fp.seek(ZIP_FILE_POSITION)


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


def debug_workers(worker_args, n_workers):
    from multiprocessing import Process, Queue, Event
    from queue import Empty

    class Worker(Process):
        def __init__(self, q: Queue, e: Event, i = 0):
            Process.__init__(self)
            self.q = q
            self.e = e
            self.i = i
        def run(self):
            file = open("./workers.%02d.log" % self.i, "w", 1)
            file.write("START: %d\n" % os.getpid())
            while True:
                try:
                    cat_name, shape_name = self.q.get(True, 1.0)
                    file.write("%s %s [   \n" % (cat_name, shape_name))
                except Empty:
                    break
                if self.e.is_set():
                    file.write("%s %s  ?  \n" % (cat_name, shape_name))
                    break
                try:
                    obj_to_blend(cat_name, shape_name)
                    file.write("%s %s    ]\n" % (cat_name, shape_name))
                except:
                    try:
                        dump = open(os.path.join(RENDER_SHAPE_NET_FOLDER, cat_name, shape_name + ".error"))
                        dump.close()
                    except:
                        pass
                    file.write("%s %s   X \n" % (cat_name, shape_name))
                    continue
                    file.write("%s %s   ! \n" % (cat_name, shape_name))
                    self.e.set()
                    raise

    s = len(worker_args)
    q = Queue()
    e = Event()

    def qsize(m: str, n: int = None):
        nonlocal s
        if n is None:
            n = q.qsize()
        d = s - n
        s = n
        t = datetime.datetime.now().isoformat(" ")
        sys.stderr.write("{} {:>5} {:>5} {} \n".format(m, d, n, t))
        sys.stderr.flush()

    if n_workers <= 0:
        raise ValueError("n >= 1 workers required")

    if n_workers == 1:
        w = Worker(q, e)
        for arg in worker_args:
            q.put_nowait(arg)
        w.run()
        return

    workers = [Worker(q, e, i) for i in range(n_workers)]
    for arg in worker_args:
        q.put_nowait(arg)

    qsize("QSIZE:")

    for worker in workers:
        worker.start()

    q.close()

    while True:
        if e.wait(10.0):
            qsize("ABORT.")
            break

        n = q.qsize()
        qsize("QSIZE:", n)

        if n == 0:
            break

        death = 0
        for worker in workers:
            if worker.exitcode:
                qsize("X{:+04d}:".format(worker.exitcode))
                death += 1

        if death:
            e.set()
            break

    qsize("JOIN1.")

    for worker in workers:
        worker.join()

    qsize("JOIN2.")


def obj_to_blend(cat_name, shape_name):
    name = cat_name + shape_name
    out_path = os.path.join(RENDER_SHAPE_NET_FOLDER, cat_name, "{}.blend".format(shape_name))

    if os.path.exists(out_path):
        bpy.ops.wm.open_mainfile(filepath=out_path)
        object = bpy.context.view_layer.objects.active = bpy.context.scene.objects[0]
        return (name, tuple(x / 2 for x in object.dimensions))

    if DIRECT_ZIP:
        pack_path = DIRECT_ZIP_MAP[cat_name + '/' + shape_name]
        file_path = os.path.join(DIRECT_ZIP_TEMP_DIR, pack_path)
        try:
            DIRECT_ZIP_FILE.extract(pack_path, DIRECT_ZIP_TEMP_DIR)
        except:
            print("TERRIBLE NO GOOD THINGS", pack_path)
            return None
    else:
        file_path = os.path.join(SIM_SHAPE_NET_FOLDER, cat_name, "{}.obj".format(shape_name))

    sys.stdout.flush()

    os.makedirs(os.path.join(RENDER_SHAPE_NET_FOLDER, cat_name), exist_ok=True)
    bpy.ops.wm.read_homefile(use_empty=True)
    # bpy.ops.object.select_all(action='SELECT')
    # bpy.ops.object.delete()

    bpy.ops.import_scene.obj(filepath=file_path, split_mode="OFF")

    if DIRECT_ZIP:
        os.unlink(file_path)

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
    bpy.ops.transform.rotate(value=-math.pi / 2, orient_axis="X")  # TODO: CHECK BLENDER API: not sure for axis
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

    bpy.ops.wm.save_as_mainfile(filepath=out_path, compress=True) # TODO: enable

    sys.stdout.flush()

    return (name, tuple(x / 2 for x in object.dimensions))



if __name__ == '__main__':
#   args = parse_args()
#   if args.start_index is None:
#       args.start_index = get_host_id() % args.stride
    args_start_index = 0
    args_stride = 1
    args_reduce = '--reduce' in sys.argv

    prepare_empty_scene_and_fix_filmic_complaints()

    if not args_reduce:
        worker_args = []

        for cat_id in SHAPE_NET_CATEGORY.keys():
            for shape_id in range(SHAPE_NET_NUMS[cat_id]):
                shape_id = "{:06d}".format(shape_id)
                worker_args.append((cat_id, shape_id))

        worker_args.sort()
        worker_args = worker_args[args_start_index::args_stride]
        worker_args = [(p, q) for p, q in worker_args if p == "0000"]

        if False:
            debug_workers(worker_args, FAST)  # TODO: increase
            sys.exit(0)

        with Pool(cpu_count(), initializer=maybe_fix_zip_file) as p:
            # TODO: this *really* should be using unordered_imap and/or a chunksize of 16
            # right now even if you have 10+ cores, only 1 will be used for the most part
            # since the task complexity is uneven and most of the workers finish early :(
            # TODO: actually switching it over from starmap causes the workers to hang :(
            # I suspect it's some cursed Blender interaction, but I can't reproduce it :(
            all_dimensions = p.starmap(obj_to_blend, worker_args, 16)
            print("starmap done")

        write_serialized(dict(all_dimensions),
                         os.path.join(SIM_SHAPE_NET_FOLDER, "all_dimensions_{:02d}.json".format(args_start_index)))
    else:
        all_dimensions = dict()
        for i in range(args_stride):
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


# 0000 001903 [02] worker.308085.log
# 0000 003249 [06] worker.308089.log
# 0000 000748 [00]

# nuke /home/bawr/.config/blender/2.82/scripts
# time PYTHONPATH=$CONDA_PREFIX/lib/python3.7/site-packages:. $BB --python-use-system-env --python ./render/data/builder/collect_blend.py 2> collect.err | tee collect.log
