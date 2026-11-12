# Arma la banda transportadora impresa en 3D dentro de Blender.
# Uso: blender -b --python armar_banda.py
# Trabaja en metros (1 mm = 0.001) y muestra las medidas en milímetros.
import bpy, math
from mathutils import Matrix, Vector

S = 0.001                      # mm -> m
SRC = "/home/claude/banda3d/"
OUT = "/home/claude/blender/out/"

PASO, Z_EJE, N_DIENTES = 10.0, 3.0, 10
R_P = PASO / (2 * math.sin(math.pi / N_DIENTES))   # radio primitivo ~16,18 mm
C = 500.0                                          # distancia entre ejes (50 eslabones por tramo recto)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'
sc.unit_settings.length_unit = 'MILLIMETERS'

# ---------- Utilidades ----------
def coleccion(nombre):
    col = bpy.data.collections.new(nombre)
    sc.collection.children.link(col)
    return col

def material(nombre, color, rugosidad=0.5, metal=0.0):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rugosidad
    b.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*color, 1)
    return m

def importar_stl(ruta, nombre, mat):
    antes = set(bpy.data.objects)
    try:
        bpy.ops.wm.stl_import(filepath=ruta)
    except Exception:
        bpy.ops.import_mesh.stl(filepath=ruta)
    obj = (set(bpy.data.objects) - antes).pop()
    me = obj.data
    me.transform(Matrix.Scale(S, 4))
    me.name = nombre
    me.materials.clear(); me.materials.append(mat)
    for p in me.polygons: p.use_smooth = False
    bpy.data.objects.remove(obj)
    return me

def malla_cilindro(nombre, radio, largo, mat, vertices=24):
    # Cilindro a lo largo del eje Y, centrado en el origen (en metros)
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radio * S, depth=largo * S,
                                        rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.active_object
    obj.data.transform(obj.matrix_world); obj.matrix_world = Matrix.Identity(4)
    me = obj.data; me.name = nombre
    me.materials.append(mat)
    bpy.data.objects.remove(obj)
    return me

def objeto(nombre, malla, col, matriz_mm):
    o = bpy.data.objects.new(nombre, malla)
    m = matriz_mm.copy()
    m.translation = m.translation * S
    o.matrix_world = m
    col.objects.link(o)
    return o

def mat4(R_cols, t):
    m = Matrix.Identity(4)
    for i in range(3):
        for j in range(3):
            m[i][j] = R_cols[j][i]
        m[i][3] = t[i]
    return m

# ---------- Materiales ----------
m_petg   = material("PETG blanco", (0.88, 0.88, 0.86), 0.45)
m_pinon  = material("PETG gris claro", (0.62, 0.64, 0.66), 0.5)
m_pasad  = material("Pasador de filamento", (0.85, 0.30, 0.08), 0.4)
m_acero  = material("Acero", (0.75, 0.75, 0.76), 0.3, 1.0)
m_motor  = material("Motor NEMA 17", (0.06, 0.06, 0.07), 0.5, 0.3)
m_suelo  = material("Mesa", (0.30, 0.31, 0.32), 0.85)
colores_mm = {"rojo": (0.75, 0.04, 0.03), "azul": (0.02, 0.18, 0.65), "amarillo": (0.95, 0.75, 0.02),
              "verde": (0.03, 0.45, 0.12), "naranja": (0.95, 0.35, 0.02), "cafe": (0.25, 0.10, 0.04)}

me_eslabon = importar_stl(SRC + "eslabon.stl", "Eslabon", m_petg)
me_pinon   = importar_stl(SRC + "pinon.stl", "Pinon", m_pinon)
me_cama    = importar_stl(SRC + "cama.stl", "Cama_deslizamiento", m_petg)
me_pasador = malla_cilindro("Pasador", 1.75 / 2, 41, m_pasad, 12)
me_eje     = malla_cilindro("Eje_8mm", 4, 80, m_acero)
me_acople  = malla_cilindro("Acople_5_8mm", 9.5, 25, m_acero)

col_banda = coleccion("Banda (110 eslabones)")
col_pas   = coleccion("Pasadores")
col_pin   = coleccion("Piñones y ejes")
col_cama  = coleccion("Cama de deslizamiento")
col_motor = coleccion("Motor")
col_mm    = coleccion("M&M de referencia")
col_amb   = coleccion("Escena")

# ---------- Recorrido de los pasadores (plano XZ) ----------
pasadores = []
for i in range(51):                                   # tramo superior
    pasadores.append((PASO * i, R_P))
for ang in (54, 18, -18, -54, -90):                   # vuelta en el piñón motriz
    a = math.radians(ang); pasadores.append((C + R_P * math.cos(a), R_P * math.sin(a)))
for i in range(1, 51):                                # tramo inferior
    pasadores.append((C - PASO * i, -R_P))
for ang in (-126, -162, -198, -234):                  # vuelta en el piñón tensor
    a = math.radians(ang); pasadores.append((R_P * math.cos(a), R_P * math.sin(a)))
assert len(pasadores) == 110

for i, (x, z) in enumerate(pasadores):
    objeto(f"Pasador_{i+1:03d}", me_pasador, col_pas, Matrix.Translation((x, 0, z)))

# ---------- Eslabones ----------
for i in range(110):
    p0 = Vector((pasadores[i][0], 0, pasadores[i][1]))
    p1 = Vector((pasadores[(i + 1) % 110][0], 0, pasadores[(i + 1) % 110][1]))
    xd = (p1 - p0).normalized()
    afuera = Vector((-xd.z, 0, xd.x))
    zd = -afuera
    yd = zd.cross(xd)
    R = (xd, yd, zd)
    Rm = Matrix((xd, yd, zd)).transposed()
    t = p0 - Rm @ Vector((0, 0, Z_EJE)) + Vector((0, 20, 0))
    objeto(f"Eslabon_{i+1:03d}", me_eslabon, col_banda, mat4(R, t))

# ---------- Piñones, ejes y motor ----------
giro = Matrix.Rotation(math.radians(-90), 4, 'X') @ Matrix.Rotation(math.radians(18), 4, 'Z')
for nombre, xc in (("Piñón tensor", 0.0), ("Piñón motriz", C)):
    objeto(nombre, me_pinon, col_pin, Matrix.Translation((xc, -20, 0)) @ giro)
    objeto("Eje " + nombre.split()[1], me_eje, col_pin, Matrix.Translation((xc, 0, 0)))

objeto("Acople motor", me_acople, col_motor, Matrix.Translation((C, 47, 0)))
bpy.ops.mesh.primitive_cube_add(size=1)
mot = bpy.context.active_object; mot.name = "Motor NEMA 17"
mot.scale = (42.3 * S, 40 * S, 42.3 * S); mot.location = (C * S, 79.5 * S, 0)
mot.data.materials.append(m_motor)
bev = mot.modifiers.new("Bisel", 'BEVEL'); bev.width = 3 * S; bev.segments = 2
for c in mot.users_collection: c.objects.unlink(mot)
col_motor.objects.link(mot)

# ---------- Cama de deslizamiento (3 tramos) ----------
z_cama = R_P - 3 - 0.3 - 3
for k in range(3):
    objeto(f"Cama_tramo_{k+1}", me_cama, col_cama, Matrix.Translation((25 + 150 * k, -18, z_cama)))

# ---------- M&M sobre la banda ----------
z_sup = R_P + Z_EJE
for (nombre, color), x, y in zip(colores_mm.items(), (95, 160, 235, 300, 370, 440), (-4, 5, -2, 3, -5, 2)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1)
    o = bpy.context.active_object; o.name = f"M&M {nombre}"
    o.scale = (6.5 * S, 6.5 * S, 3.4 * S); o.location = (x * S, y * S, (z_sup + 3.4) * S)
    bpy.ops.object.shade_smooth()
    o.data.materials.append(material(f"M&M {nombre}", color, 0.22))
    for c in o.users_collection: c.objects.unlink(o)
    col_mm.objects.link(o)

# ---------- Mesa, luces y cámaras ----------
bpy.ops.mesh.primitive_plane_add(size=1.6, location=(0.25, 0.02, -0.12))
mesa = bpy.context.active_object; mesa.name = "Mesa"; mesa.data.materials.append(m_suelo)
for c in mesa.users_collection: c.objects.unlink(mesa)
col_amb.objects.link(mesa)

def luz(nombre, tipo, energia, loc, rot=(0, 0, 0), tam=None):
    d = bpy.data.lights.new(nombre, tipo); d.energy = energia
    if tam: d.size = tam
    o = bpy.data.objects.new(nombre, d); o.location = loc; o.rotation_euler = rot
    col_amb.objects.link(o)

luz("Sol", 'SUN', 2.2, (0.3, -0.3, 0.6), (math.radians(40), math.radians(10), math.radians(30)))
luz("Luz de relleno", 'AREA', 6, (0.25, -0.35, 0.35), (math.radians(50), 0, 0), 0.6)

def camara(nombre, loc, objetivo, lente=50):
    d = bpy.data.cameras.new(nombre); d.lens = lente; d.clip_start = 0.005
    o = bpy.data.objects.new(nombre, d); o.location = loc
    vac = bpy.data.objects.new(nombre + " objetivo", None); vac.location = objetivo
    col_amb.objects.link(o); col_amb.objects.link(vac)
    tr = o.constraints.new('TRACK_TO'); tr.target = vac
    tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
    return o

cam_general = camara("Cámara general", (0.60, -0.47, 0.26), (0.285, 0.03, -0.01), 38)
cam_detalle = camara("Cámara detalle piñón", (0.565, -0.105, 0.075), (0.497, 0.0, 0.004), 50)
sc.camera = cam_general

w = bpy.data.worlds.new("Mundo"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.92, 0.93, 0.95, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.45
sc.world = w

# ---------- Render y guardado ----------
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = 48
sc.cycles.use_denoising = True
import os
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get("RX", 1600)), int(os.environ.get("RY", 900))
sc.view_settings.view_transform = 'AgX'

bpy.ops.wm.save_as_mainfile(filepath=OUT + "banda_ensamblada.blend", compress=True)
bpy.ops.export_scene.gltf(filepath=OUT + "banda_ensamblada.glb", export_format='GLB',
                          export_cameras=False, export_lights=False)

import sys
if "--render" in sys.argv:
    sc.cycles.use_denoising = False      # la instalación de prueba no trae OpenImageDenoise
    sc.cycles.samples = int(os.environ.get("SAMPLES", 48))
    sc.cycles.use_adaptive_sampling = True
    vistas = ((cam_general, "vista_general.png"), (cam_detalle, "vista_detalle_pinon.png"))
    if os.environ.get("SOLO_GENERAL"): vistas = vistas[:1]
    for cam, archivo in vistas:
        sc.camera = cam
        sc.render.filepath = OUT + archivo
        bpy.ops.render.render(write_still=True)
    sc.camera = cam_general
    sc.cycles.use_denoising = True
    sc.cycles.samples = 48
    bpy.ops.wm.save_as_mainfile(filepath=OUT + "banda_ensamblada.blend", compress=True)
print("LISTO")
