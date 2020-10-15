class ConfigClass:
    def _dumps(self, level=0):
        keys_dumped = set()
        for cls in reversed(self.__class__.__mro__):
            for k in cls.__dict__:
                if k in keys_dumped:
                    continue
                if k.startswith('_'):
                    continue
                v = getattr(self, k)
                keys_dumped.add(k)
                if isinstance(v, ConfigClass):
                    print('\t' * level, k)
                    v._dumps(level + 1)
                else:
                    print('\t' * level, k, '=', v)


class ConfigRoot(ConfigClass):

    class _Render(ConfigClass):

        class _Engine(ConfigClass):
            type = ''

        class _Cycles(_Engine):
            type = 'CYCLES'

            class _Scene(ConfigClass):
                blur_glossy = 2.0
                samples = 128
                transparent_min_bounces = 4
                transparent_max_bounces = 8

            class _World(ConfigClass):
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

    render = _RenderGPU()


Config = ConfigRoot()
Config.render.gpu_ids = [0]



if __name__ == '__main__':
    Config._dumps()
