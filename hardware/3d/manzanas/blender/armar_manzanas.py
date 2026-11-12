# Arma el clasificador de manzanas (banda de 200 mm) dentro de Blender.
# Uso: blender -b --python armar_manzanas.py            (solo genera .blend y .glb)
#      blender -b --python armar_manzanas.py -- --render (además renderiza vistas)
# Trabaja en metros (1 mm = 0.001) y muestra las medidas en milímetros.
import bpy, math, os, sys
from mathutils import Matrix, Vector

S = 0.001
SRC = "/home/claude/manzanas/"
OUT = "/home/claude/manzanas/blender/out/"

PASO, Z_EJE, N_DIENTES, ANCHO = 20.0, 4.0, 10, 200.0
R_P = PASO / (2 * math.sin(math.pi / N_DIENTES))      # ~32,36 mm
C = 1000.0                                            # 50 eslabones por tramo recto
Z_SUP = R_P + Z_EJE                                   # superficie de transporte
Y_PIN = (71.0, 0.0, -71.0)                            # 3 piñones por eje

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'
sc.unit_settings.length_unit = 'MILLIMETERS'

def coleccion(nombre):
    col = bpy.data.collections.new(nombre); sc.collection.children.link(col); return col

def material(nombre, color, rug=0.5, metal=0.0, alfa=1.0):
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rug
    b.inputs["Metallic"].default_value = metal
    if alfa < 1:
        b.inputs["Alpha"].default_value = alfa
        m.blend_method = 'BLEND'
    m.diffuse_color = (*color, alfa)
    return m

def importar_stl(ruta, nombre, mat):
    antes = set(bpy.data.objects)
    try: bpy.ops.wm.stl_import(filepath=ruta)
    except Exception: bpy.ops.import_mesh.stl(filepath=ruta)
    obj = (set(bpy.data.objects) - antes).pop()
    me = obj.data; me.transform(Matrix.Scale(S, 4)); me.name = nombre
    me.materials.clear(); me.materials.append(mat)
    for pol in me.polygons: pol.use_smooth = False
    bpy.data.objects.remove(obj); return me

def malla_cilindro(nombre, radio, largo, mat, vert=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vert, radius=radio * S, depth=largo * S, rotation=(math.pi / 2, 0, 0))
    o = bpy.context.active_object; o.data.transform(o.matrix_world)
    me = o.data; me.name = nombre; me.materials.append(mat); bpy.data.objects.remove(o); return me

def malla_caja(nombre, sx, sy, sz, mat):
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object; o.data.transform(Matrix.Diagonal((sx * S, sy * S, sz * S, 1)))
    me = o.data; me.name = nombre; me.materials.append(mat); bpy.data.objects.remove(o); return me

def objeto(nombre, malla, col, m_mm):
    o = bpy.data.objects.new(nombre, malla); m = m_mm.copy(); m.translation = m.translation * S
    o.matrix_world = m; col.objects.link(o); return o

T = Matrix.Translation
def Rz(g): return Matrix.Rotation(math.radians(g), 4, 'Z')

# ---------- Materiales ----------
m_petg  = material("PETG blanco", (0.88, 0.88, 0.86), 0.45)
m_pin   = material("PETG gris", (0.55, 0.57, 0.6), 0.5)
m_pas   = material("Pasador de filamento", (0.85, 0.30, 0.08), 0.4)
m_acero = material("Acero", (0.75, 0.75, 0.76), 0.3, 1.0)
m_negro = material("Motor y servos", (0.05, 0.05, 0.06), 0.5, 0.2)
m_pal   = material("Paletas (PETG azul)", (0.10, 0.35, 0.75), 0.45)
m_mesa  = material("Mesa", (0.30, 0.31, 0.32), 0.85)
m_tunel = material("Túnel (pendiente)", (0.3, 0.6, 0.9), 0.3, 0.0, 0.12)

me_esl   = importar_stl(SRC + "eslabon.stl", "Eslabon_200", m_petg)
me_pinon = importar_stl(SRC + "pinon.stl", "Pinon_20", m_pin)
me_cama  = importar_stl(SRC + "cama.stl", "Cama_escalera", m_petg)
me_pal   = importar_stl(SRC + "paleta.stl", "Paleta_300", m_pal)
me_sop   = importar_stl(SRC + "soporte_servo.stl", "Soporte_MG996R", m_pin)
me_pas   = malla_cilindro("Pasador_200", 1.75 / 2, 201, m_pas, 10)
me_eje   = malla_cilindro("Eje_8mm", 4, 260, m_acero)
me_acop  = malla_cilindro("Acople_5_8mm", 9.5, 25, m_acero)
me_servo = malla_caja("MG996R", 40.7, 19.7, 42.9, m_negro)
me_brazo = malla_caja("Brazo_servo", 44, 9, 4, m_petg)

col_banda = coleccion("Banda (110 eslabones)")
col_pas   = coleccion("Pasadores")
col_pin   = coleccion("Piñones y ejes")
col_cama  = coleccion("Cama de deslizamiento")
col_desv  = coleccion("Desviadores")
col_motor = coleccion("Motor")
col_mz    = coleccion("Manzanas de referencia")
col_amb   = coleccion("Escena")

# ---------- Recorrido de los pasadores ----------
pas = [(PASO * i, R_P) for i in range(51)]
pas += [(C + R_P * math.cos(math.radians(a)), R_P * math.sin(math.radians(a))) for a in (54, 18, -18, -54, -90)]
pas += [(C - PASO * i, -R_P) for i in range(1, 51)]
pas += [(R_P * math.cos(math.radians(a)), R_P * math.sin(math.radians(a))) for a in (-126, -162, -198, -234)]
assert len(pas) == 110

for i, (x, z) in enumerate(pas):
    objeto(f"Pasador_{i+1:03d}", me_pas, col_pas, T((x, 0, z)))

for i in range(110):
    p0 = Vector((pas[i][0], 0, pas[i][1])); p1 = Vector((pas[(i + 1) % 110][0], 0, pas[(i + 1) % 110][1]))
    xd = (p1 - p0).normalized(); zd = -Vector((-xd.z, 0, xd.x)); yd = zd.cross(xd)
    R = Matrix((xd, yd, zd)).transposed()
    m = R.to_4x4(); m.translation = p0 - R @ Vector((0, 0, Z_EJE)) + Vector((0, ANCHO / 2, 0))
    objeto(f"Eslabon_{i+1:03d}", me_esl, col_banda, m)

# ---------- Piñones (3 por eje), ejes y motor ----------
giro = Matrix.Rotation(math.radians(-90), 4, 'X') @ Rz(18)
for nombre, xc in (("tensor", 0.0), ("motriz", C)):
    for k, yc in enumerate(Y_PIN):
        objeto(f"Piñón {nombre} {k+1}", me_pinon, col_pin, T((xc, yc - 7, 0)) @ giro)
    objeto(f"Eje {nombre}", me_eje, col_pin, T((xc, 0, 0)))
objeto("Acople motor", me_acop, col_motor, T((C, 142, 0)))
me_mot = malla_caja("NEMA17", 42.3, 40, 42.3, m_negro)
objeto("Motor NEMA 17", me_mot, col_motor, T((C, 175, 0)))

# ---------- Cama de deslizamiento: 5 tramos de 180 mm ----------
z_cama = R_P - 4 - 0.3 - 3
for k in range(5):
    objeto(f"Cama_tramo_{k+1}", me_cama, col_cama, T((50 + 180 * k, -100, z_cama)))

# ---------- Desviadores ----------
# Paleta 1: pivote en el lado -Y (x = 450), cerrada a 45°, manda a la salida +Y.
# Paleta 2: pivote en el lado +Y (x = 750), abierta, mandaría a la salida -Y.
z_pal = Z_SUP + 2
z_servo = z_pal + 46 + 4 + 1          # cara del eje del servo
for nombre, (xp, yp, ang, signo) in {"1": (450, -112, 45, -1), "2": (750, 112, 0, 1)}.items():
    objeto(f"Paleta {nombre}", me_pal, col_desv, T((xp, yp, z_pal)) @ Rz(ang))
    objeto(f"Brazo servo {nombre}", me_brazo, col_desv, T((xp, yp, z_pal + 46 - 1.5)) @ Rz(ang))
    xc = xp + 10.15                  # el eje del MG996R está a 10,2 mm de un extremo; cuerpo aguas abajo
    objeto(f"Servo MG996R {nombre}", me_servo, col_desv, T((xc, yp, z_servo + 21.45)))
    rot = Rz(0 if signo < 0 else 180)
    objeto(f"Soporte servo {nombre}", me_sop, col_desv, T((xc, yp, z_servo + 13)) @ rot)

# ---------- Túnel de cámara (volumen reservado, aún sin diseñar) ----------
me_t = malla_caja("Tunel_volumen", 160, 260, 220, m_tunel)
objeto("Túnel de cámara (volumen reservado)", me_t, col_amb, T((280, 0, Z_SUP + 110)))

# ---------- Manzanas ----------
colores = {"roja": (0.55, 0.03, 0.03), "verde": (0.35, 0.6, 0.08), "amarilla": (0.85, 0.65, 0.08), "roja 2": (0.6, 0.06, 0.04)}
for (nombre, color), (x, y) in zip(colores.items(), ((80, 0), (280, 0), (553, 46), (880, -5))):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1)
    o = bpy.context.active_object; o.name = f"Manzana {nombre}"
    o.scale = (39 * S, 39 * S, 35 * S); o.location = (x * S, y * S, (Z_SUP + 35) * S)
    bpy.ops.object.shade_smooth(); o.data.materials.append(material(f"Manzana {nombre}", color, 0.35))
    for c in o.users_collection: c.objects.unlink(o)
    col_mz.objects.link(o)

# ---------- Mesa, luces, cámaras ----------
bpy.ops.mesh.primitive_plane_add(size=2.8, location=(0.5, 0.0, -0.15))
mesa = bpy.context.active_object; mesa.name = "Mesa"; mesa.data.materials.append(m_mesa)
for c in mesa.users_collection: c.objects.unlink(mesa)
col_amb.objects.link(mesa)

def luz(nombre, tipo, energia, loc, rot=(0, 0, 0), tam=None):
    d = bpy.data.lights.new(nombre, tipo); d.energy = energia
    if tam: d.size = tam
    o = bpy.data.objects.new(nombre, d); o.location = loc; o.rotation_euler = rot; col_amb.objects.link(o)

luz("Sol", 'SUN', 2.2, (0.4, -0.4, 1.0), (math.radians(40), math.radians(10), math.radians(30)))
luz("Relleno", 'AREA', 30, (0.5, -0.8, 0.75), (math.radians(45), 0, 0), 1.4)

def camara(nombre, loc, obj, lente):
    d = bpy.data.cameras.new(nombre); d.lens = lente; d.clip_start = 0.005
    o = bpy.data.objects.new(nombre, d); o.location = loc
    v = bpy.data.objects.new(nombre + " objetivo", None); v.location = obj
    col_amb.objects.link(o); col_amb.objects.link(v)
    t = o.constraints.new('TRACK_TO'); t.target = v; t.track_axis = 'TRACK_NEGATIVE_Z'; t.up_axis = 'UP_Y'
    return o

cam_g = camara("Cámara general", (1.38, -1.15, 0.74), (0.52, 0.0, 0.02), 35)
cam_d = camara("Cámara desviador", (0.75, -0.42, 0.34), (0.55, 0.0, 0.05), 35)
sc.camera = cam_g

w = bpy.data.worlds.new("Mundo"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.92, 0.93, 0.95, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.45
sc.world = w

sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
sc.cycles.samples = 48; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get("RX", 1600)), int(os.environ.get("RY", 900))
sc.view_settings.view_transform = 'AgX'

bpy.ops.wm.save_as_mainfile(filepath=OUT + "clasificador_manzanas.blend", compress=True)
bpy.ops.export_scene.gltf(filepath=OUT + "clasificador_manzanas.glb", export_format='GLB',
                          export_cameras=False, export_lights=False)

if "--render" in sys.argv:
    sc.cycles.use_denoising = False
    sc.cycles.samples = int(os.environ.get("SAMPLES", 40))
    vistas = [(cam_g, "vista_general.png"), (cam_d, "vista_desviador.png")]
    if os.environ.get("VISTA"): vistas = [v for v in vistas if os.environ["VISTA"] in v[1]]
    for cam, archivo in vistas:
        sc.camera = cam; sc.render.filepath = OUT + archivo
        bpy.ops.render.render(write_still=True)
    sc.camera = cam_g; sc.cycles.use_denoising = True; sc.cycles.samples = 48
    bpy.ops.wm.save_as_mainfile(filepath=OUT + "clasificador_manzanas.blend", compress=True)
print("LISTO")
