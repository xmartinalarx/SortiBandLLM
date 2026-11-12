"""Consultas a MySQL del servidor (registro de manzanas, lotes y estadísticas).

Las horas que se guardan son las del PC servidor al recibir cada mensaje: así no
importa si el reloj del Arduino está desfasado o sin hora (sin NTP).
"""
from datetime import datetime, timedelta

from comun import config
from comun.db import conectar


# ---------- Lotes ----------
def lote_abierto() -> int | None:
    with conectar() as con, con.cursor() as cur:
        cur.execute("SELECT id FROM batches WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1")
        fila = cur.fetchone()
    return fila["id"] if fila else None


def abrir_lote() -> int:
    with conectar() as con, con.cursor() as cur:
        cur.execute("INSERT INTO batches (started_at, product) VALUES (%s, %s)", (datetime.now(), config.PRODUCTO))
        return cur.lastrowid


def cerrar_lote(batch_id: int) -> None:
    with conectar() as con, con.cursor() as cur:
        cur.execute("UPDATE batches SET ended_at = %s WHERE id = %s", (datetime.now(), batch_id))


def lote_actual_o_ultimo() -> dict | None:
    """El lote abierto, o si no hay, el último que se cerró (para que el dashboard muestre algo)."""
    with conectar() as con, con.cursor() as cur:
        cur.execute("SELECT * FROM batches ORDER BY (ended_at IS NULL) DESC, id DESC LIMIT 1")
        return cur.fetchone()


# ---------- Manzanas ----------
def _fila_de_pieza(cur, batch_id: int | None, piece_id: int) -> int | None:
    """Id de la fila más reciente de esa manzana en el lote. Se toma la más reciente
    porque el contador del Arduino vuelve a 1 si se reinicia."""
    cur.execute(
        "SELECT id FROM pieces WHERE batch_id <=> %s AND piece_id = %s ORDER BY id DESC LIMIT 1",
        (batch_id, piece_id),
    )
    fila = cur.fetchone()
    return fila["id"] if fila else None


def registrar_llegada(batch_id: int | None, piece_id: int) -> None:
    with conectar() as con, con.cursor() as cur:
        cur.execute(
            "INSERT INTO pieces (batch_id, piece_id, ts) VALUES (%s, %s, %s)",
            (batch_id, piece_id, datetime.now()),
        )


def registrar_resultado(batch_id: int | None, datos: dict) -> None:
    valores = (datos.get("color"), bool(datos.get("is_defective")), datos.get("confidence"),
               datos.get("output_channel"), datos.get("image_path"))
    with conectar() as con, con.cursor() as cur:
        fila = _fila_de_pieza(cur, batch_id, datos["piece_id"])
        if fila is None:
            # No se vio la llegada (por ejemplo, el servidor partió tarde): se crea la fila
            cur.execute(
                "INSERT INTO pieces (batch_id, piece_id, ts, color, is_defective, confidence, "
                "output_channel, image_path) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (batch_id, datos["piece_id"], datetime.now(), *valores),
            )
        else:
            cur.execute(
                "UPDATE pieces SET color=%s, is_defective=%s, confidence=%s, output_channel=%s, "
                "image_path=%s WHERE id=%s",
                (*valores, fila),
            )


def registrar_desvio(batch_id: int | None, piece_id: int, output_channel: int) -> None:
    """Guarda la salida REAL (puede diferir de la pedida si no llegó el resultado a tiempo
    o si la paleta estaba ocupada)."""
    with conectar() as con, con.cursor() as cur:
        fila = _fila_de_pieza(cur, batch_id, piece_id)
        if fila is None:
            cur.execute(
                "INSERT INTO pieces (batch_id, piece_id, ts, output_channel, diverted_ts) "
                "VALUES (%s, %s, %s, %s, %s)",
                (batch_id, piece_id, datetime.now(), output_channel, datetime.now()),
            )
        else:
            cur.execute(
                "UPDATE pieces SET output_channel=%s, diverted_ts=%s WHERE id=%s",
                (output_channel, datetime.now(), fila),
            )


# ---------- Consultas para el dashboard ----------
def estadisticas(batch_id: int) -> dict:
    with conectar() as con, con.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(is_defective), 0) AS defectuosas, "
            "AVG(confidence) AS confianza FROM pieces WHERE batch_id = %s",
            (batch_id,),
        )
        resumen = cur.fetchone()

        cur.execute(
            "SELECT color, COUNT(*) AS n FROM pieces WHERE batch_id = %s AND color IS NOT NULL "
            "GROUP BY color ORDER BY n DESC",
            (batch_id,),
        )
        por_color = {f["color"]: f["n"] for f in cur.fetchall()}

        cur.execute(
            "SELECT output_channel, COUNT(*) AS n FROM pieces WHERE batch_id = %s "
            "AND output_channel IS NOT NULL GROUP BY output_channel",
            (batch_id,),
        )
        por_salida = {str(f["output_channel"]): f["n"] for f in cur.fetchall()}

        # Manzanas por minuto: las que llegaron en los últimos 60 s
        cur.execute(
            "SELECT COUNT(*) AS n FROM pieces WHERE batch_id = %s AND ts >= %s",
            (batch_id, datetime.now() - timedelta(seconds=60)),
        )
        por_minuto = cur.fetchone()["n"]

    total = int(resumen["total"])
    defectuosas = int(resumen["defectuosas"])
    return {
        "total": total,
        "defectuosas": defectuosas,
        "pct_defectuosas": round(100 * defectuosas / total, 1) if total else 0,
        "confianza_promedio": round(float(resumen["confianza"]), 3) if resumen["confianza"] is not None else None,
        "por_minuto": por_minuto,
        "por_color": por_color,
        "por_salida": por_salida,
    }


def ultimas_piezas(limite: int) -> list[dict]:
    with conectar() as con, con.cursor() as cur:
        cur.execute(
            "SELECT id, batch_id, piece_id, ts, color, is_defective, confidence, output_channel, "
            "image_path, diverted_ts FROM pieces ORDER BY id DESC LIMIT %s",
            (limite,),
        )
        return cur.fetchall()


def ultimas_rechazadas(limite: int) -> list[dict]:
    with conectar() as con, con.cursor() as cur:
        cur.execute(
            "SELECT id, piece_id, ts, color, confidence, image_path FROM pieces "
            "WHERE is_defective = TRUE AND image_path IS NOT NULL ORDER BY id DESC LIMIT %s",
            (limite,),
        )
        return cur.fetchall()
