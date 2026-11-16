# Actualiza la escena del clasificador (clasificador_manzanas.blend) con el diseño vigente
# y renderiza la vista general. Agrega lo decidido después de armar la escena original:
#   - base de madera (115 x 40 cm), 2 laterales (112 x 9,4 cm) y 2 listones para la cama
#   - ejes de 300 mm (sin cortar) con porta-rodamientos 608 por fuera de los laterales
#   - motor 28BYJ-48 con su soporte y acople (reemplaza al NEMA 17)
#   - sensor IR en x = 170, túnel de cartón con webcam (opcional) y la electrónica sobre la base
#
# Uso (desde esta carpeta):
#   blender -b --python actualizar_escena.py                 (solo guarda clasificador_manzanas_v2.blend)
#   blender -b --python actualizar_escena.py -- --render     (además renderiza ../imagenes/vista_general_actualizada.png)
# Unidades: la escena está en metros; aquí se trabaja en mm (S = 0,001).
import bpy, math, os, sys
from mathutils import Matrix

AQUI = os.path.dirname(os.path.abspath(__file__))
S = 0.001
T = Matrix.Translation

bpy.ops.wm.open_mainfile(filepath=os.path.join(AQUI, "clasificador_manzanas.blend"))
sc = bpy.context.scene

def material(nombre, color, rug=0.5, metal=0.0):
    m = bpy.data.materials.new(nombre); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rug
    b.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*color, 1)
    return m

def coleccion(nombre):
    col = bpy.data.collections.new(nombre); sc.collection.children.link(col); return col

def caja(nombre, col, mat, centro, tam):
    """Caja de tamaño tam = (x, y, z) mm con su centro en centro = (x, y, z) mm."""
    bpy.ops.mesh.primitive_cube_add(size=1)
    o = bpy.context.active_object; o.name = nombre
    o.data.transform(Matrix.Diagonal((tam[0] * S, tam[1] * S, tam[2] * S, 1)))
    o.location = tuple(c * S for c in centro)
    o.data.materials.append(mat)
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o); return o

def cilindro(nombre, col, mat, centro, radio, largo, eje='Y', vert=32):
    rot = {'Y': (math.pi / 2, 0, 0), 'Z': (0, 0, 0), 'X': (0, math.pi / 2, 0)}[eje]
    bpy.ops.mesh.primitive_cylinder_add(vertices=vert, radius=radio * S, depth=largo * S, rotation=rot)
    o = bpy.context.active_object; o.name = nombre
    o.location = tuple(c * S for c in centro)
    o.data.materials.append(mat); bpy.ops.object.shade_smooth()
    for c in o.users_collection: c.objects.unlink(o)
    col.objects.link(o); return o

def borrar(nombre):
    o = bpy.data.objects.get(nombre)
    if o: bpy.data.objects.remove(o)

# ---------- Quitar lo que cambió ----------
for n in ("Motor NEMA 17", "Acople motor", "Túnel de cámara (volumen reservado)", "Eje tensor", "Eje motriz"):
    borrar(n)

# ---------- Materiales nuevos ----------
m_madera  = material("Madera (MDF/terciado)", (0.55, 0.32, 0.13), 0.7)
m_liston  = material("Listón de pino", (0.62, 0.40, 0.18), 0.7)
m_acero   = bpy.data.materials.get("Acero") or material("Acero", (0.75, 0.75, 0.76), 0.3, 1.0)
m_gris    = bpy.data.materials.get("PETG gris") or material("PETG gris", (0.55, 0.57, 0.6), 0.5)
m_motor   = material("Carcasa 28BYJ-48", (0.70, 0.71, 0.73), 0.35, 0.8)
m_azul    = material("Tapa azul 28BYJ-48", (0.10, 0.25, 0.70), 0.5)
m_negro   = material("Plástico negro", (0.03, 0.03, 0.035), 0.5)
m_rojo    = material("Rojo", (0.75, 0.05, 0.04), 0.4)
m_carton  = material("Cartón (exterior)", (0.36, 0.26, 0.17), 0.95)
m_arduino = material("PCB Arduino (teal)", (0.0, 0.42, 0.45), 0.5)
m_pcb     = material("PCB verde", (0.05, 0.35, 0.12), 0.5)
m_proto   = material("Protoboard", (0.93, 0.93, 0.90), 0.6)
m_vidrio  = material("Lente", (0.02, 0.02, 0.05), 0.05, 0.5)

col_base = coleccion("Base de madera")
col_ejes = coleccion("Ejes y rodamientos")
col_mot  = coleccion("Motor 28BYJ-48")
col_elec = coleccion("Electrónica y sensores")
col_tun  = coleccion("Túnel de cartón (opcional)")

# Referencias (mm): eje tensor en x = 0, eje motriz en x = 1000, centro de los ejes en z = 0,
# banda centrada en y = 0. Base de madera: su cara de arriba queda a 70 mm bajo los ejes.
Z_BASE = -70.0

# ---------- Base de madera ----------
caja("Base 115 x 40 cm", col_base, m_madera, (500, 0, Z_BASE - 9), (1150, 400, 18))
for lado, s in (("A", -1), ("B", 1)):
    # Lateral 112 x 9,4 x 1,8 cm: desde x = -60 (punta) hasta 1060; caras interiores a ±105 mm
    caja(f"Lateral {lado} 112 x 9,4 cm", col_base, m_madera, (500, s * 114, Z_BASE + 47), (1120, 18, 94))
    # Listón 90 x 2 x 2 cm por dentro, al ras arriba (x = 50 a 950)
    caja(f"Listón cama {lado}", col_base, m_liston, (500, s * 95, 14), (900, 20, 20))

# ---------- Ejes de 300 mm, porta-rodamientos y rodamientos ----------
cilindro("Eje tensor 300 mm", col_ejes, m_acero, (0, 0, 0), 4, 300)
cilindro("Eje motriz 300 mm", col_ejes, m_acero, (1000, 15, 0), 4, 300)   # sobrante hacia el motor
for xc, nombre, largo_x in ((0, "tensor", 64), (1000, "motriz", 44)):
    for s in (-1, 1):
        caja(f"Porta-rodamiento {nombre} {'+' if s > 0 else '-'}", col_ejes, m_gris, (xc, s * 129, 0), (largo_x, 12, 44))
        cilindro(f"Rodamiento 608 {nombre} {'+' if s > 0 else '-'}", col_ejes, m_acero, (xc, s * 136, 0), 11, 3)

# ---------- Motor 28BYJ-48 + acople + soporte ----------
cilindro("Acople 5-8 mm", col_mot, m_acero, (1000, 158, 0), 9.5, 25)
cilindro("Motor 28BYJ-48", col_mot, m_motor, (1000, 181, -8), 14, 19)      # su eje está 8 mm sobre el centro
cilindro("Tapa reductora", col_mot, m_azul, (1000, 171, 0), 4.5, 3)
caja("Caja de cables del motor", col_mot, m_azul, (1000, 186, -22), (17, 14, 6))
caja("Soporte del motor (impreso)", col_mot, m_gris, (1000, 181, (Z_BASE - 22) / 2), (44, 24, Z_BASE * -1 - 22))
caja("Placa ULN2003", col_elec, m_pcb, (905, 165, Z_BASE + 2), (35, 32, 1.6))
caja("Chip ULN2003", col_elec, m_negro, (905, 160, Z_BASE + 4), (20, 7, 3))

# ---------- Sensor IR de barrera (x = 170), sobre los laterales ----------
for s, nombre in ((-1, "emisor"), (1, "receptor")):
    caja(f"Sensor IR {nombre}", col_elec, m_negro, (170, s * 114, 34), (12, 12, 20))
    cilindro(f"Lente IR {nombre}", col_elec, m_rojo, (170, s * 107, 38), 2.5, 2)

# ---------- Electrónica sobre la base (franja libre del lado -Y) ----------
caja("Arduino UNO R4 WiFi", col_elec, m_arduino, (640, -162, Z_BASE + 4), (68.6, 53.4, 1.6))
caja("Conector USB-C", col_elec, m_acero, (604, -162, Z_BASE + 7), (8, 9, 3.5))
caja("Módulo WiFi R4", col_elec, m_acero, (668, -150, Z_BASE + 6), (16, 18, 2.5))
for i in range(2):
    caja(f"Header {i+1}", col_elec, m_negro, (640, -162 + (i * 2 - 1) * 24, Z_BASE + 8), (60, 2.5, 8))
caja("Protoboard", col_elec, m_proto, (770, -162, Z_BASE + 4.5), (82, 55, 9))
caja("Pulsador de emergencia (base)", col_elec, m_negro, (880, -165, Z_BASE + 2.5), (14, 14, 5))
cilindro("Pulsador de emergencia (botón)", col_elec, m_rojo, (880, -165, Z_BASE + 7), 5, 4, eje='Z')

# ---------- Túnel de cartón (x = 200 a 360) con webcam ----------
Z_TECHO = 250.0
alto_pared = Z_TECHO - Z_BASE
for s in (-1, 1):
    caja(f"Túnel pared {'+' if s > 0 else '-'}", col_tun, m_carton, (280, s * 131.5, Z_BASE + alto_pared / 2), (160, 3, alto_pared))
caja("Túnel techo", col_tun, m_carton, (280, 0, Z_TECHO + 1.5), (160, 266, 3))
caja("Webcam", col_tun, m_negro, (280, 0, Z_TECHO + 15), (90, 26, 26))
cilindro("Lente webcam", col_tun, m_vidrio, (280, -13.5, Z_TECHO + 15), 6, 2)
caja("Pinza webcam", col_tun, m_negro, (280, 0, Z_TECHO + 4), (30, 30, 5))

# ---------- Mesa a la altura de la base y render ----------
mesa = bpy.data.objects.get("Mesa")
if mesa: mesa.location.z = (Z_BASE - 18) * S

def usar_gpu():
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for tipo in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = tipo
                prefs.get_devices()
                usadas = [d for d in prefs.devices if d.type == tipo]
                if usadas:
                    for d in prefs.devices: d.use = d.type == tipo
                    sc.cycles.device = 'GPU'
                    print("Render con GPU:", tipo, [d.name for d in usadas]); return
            except Exception:
                pass
    except Exception:
        pass
    sc.cycles.device = 'CPU'; print("Render con CPU")

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(AQUI, "clasificador_manzanas_v2.blend"), compress=True)

if "--render" in sys.argv:
    usar_gpu()
    sc.cycles.samples = int(os.environ.get("SAMPLES", 96)); sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get("RX", 1600)), int(os.environ.get("RY", 900))
    # Segunda cámara: desde atrás, para ver el motor, su soporte y el acople
    d = bpy.data.cameras.new("Cámara trasera"); d.lens = 35; d.clip_start = 0.005
    cam_t = bpy.data.objects.new("Cámara trasera", d); cam_t.location = (1.45, 1.05, 0.62)
    obj_t = bpy.data.objects.new("Cámara trasera objetivo", None); obj_t.location = (0.62, 0.0, 0.0)
    sc.collection.objects.link(cam_t); sc.collection.objects.link(obj_t)
    tr = cam_t.constraints.new('TRACK_TO'); tr.target = obj_t; tr.track_axis = 'TRACK_NEGATIVE_Z'; tr.up_axis = 'UP_Y'
    vistas = [("Cámara general", "vista_general_actualizada.png"), ("Cámara trasera", "vista_trasera_actualizada.png")]
    if os.environ.get("SALIDA"): vistas = [("Cámara general", os.environ["SALIDA"])]
    for nombre_cam, archivo in vistas:
        sc.camera = bpy.data.objects.get(nombre_cam)
        sc.render.filepath = os.path.join(AQUI, "..", "imagenes", archivo)
        bpy.ops.render.render(write_still=True)
print("LISTO")
