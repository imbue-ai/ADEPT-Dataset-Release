import sys

print(sys.version)
print(sys.argv)
print()

for p, i in sorted(zip(sys.path, range(len(sys.path)))):
    print("%3d %s" % (i, p))

print()

try:
    import bpy
except ImportError:
    for k in sorted(dir(bpy.app.build_options)):
        if k.startswith('__'):
            continue
        if k in ('count', 'index'):
            continue
        print(k, getattr(bpy.app.build_options, k))

print()
