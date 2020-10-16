import ast
import multiprocessing


# TODO: TOML
class _Settings:
    def _lines(self, path=()):
        lines = []
        keys_dumped = set()
        for cls in reversed(self.__class__.__mro__):
            for k in cls.__dict__:
                if k in keys_dumped:
                    continue
                if k.startswith('_'):
                    continue
                v = getattr(self, k)
                p = (*path, k)
                keys_dumped.add(k)
                if isinstance(v, _Settings):
                    lines.extend(v._lines(p))
                else:
                    v = repr(v)
                    assert '=' not in v
                    assert '#' not in v
                    lines.append('%s = %s' % ('.'.join(p), v))
        return lines

    def _dumps(self):
        lines = self._lines()
        lines.append('')
        return '\n'.join(lines)

    def _loads(self, data):
        kvs = [
            line.split(' = ') for line in data.split('\n') if line and not line.startswith('#')
        ]
        for k, v in kvs:
            [*p, k] = k.split('.')
            v = ast.literal_eval(v)
            obj = self
            for q in p:
                obj = getattr(obj, q)
            setattr(obj, k, v)



class _Config(_Settings):

    class _Render(_Settings):

        class _Engine(_Settings):
            type = ''

        class _Cycles(_Engine):
            type = 'CYCLES'

            class _Scene(_Settings):
                blur_glossy = 2.0
                samples = 128
                transparent_min_bounces = 4
                transparent_max_bounces = 8

            class _World(_Settings):
                sample_as_light = True

            scene = _Scene()
            world = _World()

        cpu_use = 0
        gpu_use = 0
        gpu_ids = [0, 1, 2, 3, 4, 5, 6, 7, 8]

        tile_x = -1
        tile_y = -1

        fps = 25

        resolution_x = 480
        resolution_y = 320

        resolution_percentage = 100

        engine = _Cycles()

    class _RenderCPU(_Render):
        cpu_use = 1
        gpu_use = 0
        tile_x = 16
        tile_y = 16

    class _RenderGPU(_Render):
        cpu_use = 0
        gpu_use = 1
        tile_x = 160
        tile_y = 160

    class _Data(_Settings):
        shape_net_use = True
        shape_net_zip = ""
        shape_net_dir = ""
        shape_net_tmp = "/dev/shm/shape_net_tmp"
        shape_net_cpu = multiprocessing.cpu_count()

    class _Misc(_Settings):
        blender_silent = 1
        blender_packed = 1

    data = _Data()
    misc = _Misc()
    render = _RenderGPU()



Config = _Config()
Config.render.gpu_ids = [0]
Config.data.shape_net_use = 1
Config.data.shape_net_zip = "/media/bawr/ev850/data/ShapeNetCore.v2/ShapeNetCore.v2.zip"
Config.data.shape_net_dir = "/media/bawr/ev850/data_adept/blend_net/"
Config.data.shape_net_cpu = 10



if __name__ == '__main__':
    print(Config._dumps())
