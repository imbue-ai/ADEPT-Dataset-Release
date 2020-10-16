# Rendering numbers

Time to 125 frames: (a single 5s video)

| Machine | Cores   | GPU          | Renderer | Blender  | Width | Height | Size | Time  |
|---------|--------:|--------------|----------|---------:|------:|-------:|-----:|------:|
| bawr pc |  1 / 12 | GTX 1080 x 2 | Cycles   |  py-2.83 |   480 |    320 | 30MB |  3:43 |
| bawr pc |  1 / 12 | GTX 1080 x 1 | Cycles   |  py-2.83 |   480 |    320 | 30MB |  4:24 |
| bawr pc | 12 / 12 | -            | Cycles   |  py-2.83 |   480 |    320 | 30MB | 20:32 |
| bawr pc |  1 / 12 | GTX 1080 x 1 | Eevee    | sys-2.82 |   480 |    320 | 30MB |  1:04 |
| gcp     |  1 / 4  | Tesla T4     | Cycles   | py-2.83  |   480 |    320 | 30MB |  6:01 |
