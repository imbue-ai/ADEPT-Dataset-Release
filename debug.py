import sys

print(sys.version)
print(sys.argv)
print()

for p, i in sorted(zip(sys.path, range(len(sys.path)))):
    print("%3d %s" % (i, p))
