# Banda ensamblada en Blender

| Archivo | Qué es |
|---|---|
| `banda_ensamblada.blend` | Escena completa para Blender 4.0 o más nuevo |
| `banda_ensamblada.glb` | La misma banda en formato glTF: se abre en Blender (Archivo > Importar > glTF), en el Visor 3D de Windows o en visores web |
| `vista_general.png`, `vista_detalle_pinon.png` | Renders de referencia |
| `armar_banda.py` | Script que genera la escena a partir de los STL (`blender -b --python armar_banda.py`) |

## Qué contiene la escena

- **Banda (110 eslabones):** envuelta en los dos piñones, 50 eslabones por tramo recto.
- **Pasadores:** 110 trozos de filamento de 1,75 mm, en naranja para que se vean.
- **Piñones y ejes:** piñón tensor (izquierda) y motriz (derecha), ejes de 8 mm a 500 mm entre centros.
- **Cama de deslizamiento:** 3 tramos de 150 mm bajo el tramo superior.
- **Motor:** NEMA 17 con acople al eje motriz (bloque simplificado).
- **M&M de referencia:** 6 piezas de 13 mm para dar escala.

Cada grupo está en su propia colección, así que puedes ocultarlo desde el panel Outliner. Los eslabones son copias enlazadas del mismo modelo: si editas uno, cambian todos.

## Cómo usarla

- **Medidas:** la escena trabaja en metros y muestra milímetros. Con la tecla N ves las dimensiones de cada objeto.
- **Cámaras:** hay dos, "Cámara general" y "Cámara detalle piñón". Selecciona una y presiona Ctrl + 0 numérico para mirar por ella.
- **Render:** F12 (Cycles, 48 muestras con eliminación de ruido).
- **Vista rápida:** presiona Z y elige "Material Preview".

El bastidor (laterales, soportes de rodamientos y tensor) aún no está incluido.
