"""
API de IKA: panel, clientes, inventario, cotizaciones, notas de entrega,
documentos y ajustes. Todo bajo /api.
"""
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, send_file

import pdfs
from config import DATA_DIR, DOCS_DIR, LOGO_DEFAULT
from db import config, config_todo, get_db

bp = Blueprint("api", __name__, url_prefix="/api")

ESTADOS_COT = ("borrador", "enviada", "aprobada", "rechazada", "vencida")
ABIERTAS = ("borrador", "enviada")
CATEGORIAS = ("energia", "cctv", "red", "personal", "otro")
LOGO_SUBIDO = DATA_DIR / "logo.png"


class ErrorApi(Exception):
    def __init__(self, mensaje, status=400):
        super().__init__(mensaje)
        self.status = status


@bp.errorhandler(ErrorApi)
def _error(e):
    return jsonify({"error": str(e)}), e.status


def _json():
    return request.get_json(silent=True) or {}


def _fila(row):
    return dict(row) if row else None


def _num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _texto(v):
    v = (v or "").strip() if isinstance(v, str) else v
    return v or None


def _logo():
    return LOGO_SUBIDO if LOGO_SUBIDO.exists() else LOGO_DEFAULT


def _nombre_seguro(texto: str) -> str:
    limpio = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", texto or "").strip(" .")
    return re.sub(r"\s+", " ", limpio)[:60].strip() or "Sin nombre"


def _ruta_larga(ruta):
    r"""Prefijo \\?\ para que Windows acepte rutas de más de 260 caracteres
    (la carpeta de OneDrive ya ocupa buena parte del límite)."""
    if sys.platform == "win32":
        return Path("\\\\?\\" + str(ruta.resolve()))
    return ruta


def _siguiente_folio(db, tabla, prefijo):
    base = f"{prefijo}-{date.today().year}-"
    maximo = 0
    for r in db.execute(f"SELECT folio FROM {tabla} WHERE folio LIKE ?", (base + "%",)):
        m = re.match(rf"^{re.escape(base)}(\d+)", r["folio"])
        if m:
            maximo = max(maximo, int(m.group(1)))
    return f"{base}{maximo + 1:03d}"


def _marcar_vencidas(db):
    db.execute(
        """UPDATE cotizaciones SET estado = 'vencida'
           WHERE estado = 'enviada' AND eliminada = 0
             AND date(fecha, '+' || vigencia_dias || ' days') < date('now','localtime')"""
    )
    db.commit()


# ================================================================== panel

@bp.get("/panel")
def panel():
    db = get_db()
    _marcar_vencidas(db)
    abiertas = db.execute(
        f"""SELECT COUNT(*) n, COALESCE(SUM(total),0) monto FROM cotizaciones
            WHERE eliminada = 0 AND estado IN {ABIERTAS}"""
    ).fetchone()
    mes = db.execute(
        """SELECT COUNT(*) n, COALESCE(SUM(total),0) monto FROM cotizaciones
           WHERE eliminada = 0 AND estado = 'aprobada'
             AND strftime('%Y-%m', actualizada) = strftime('%Y-%m','now','localtime')"""
    ).fetchone()
    por_vencer = db.execute(
        """SELECT c.id, c.folio, c.total, cl.nombre cliente,
                  date(c.fecha, '+' || c.vigencia_dias || ' days') vence
           FROM cotizaciones c LEFT JOIN clientes cl ON cl.id = c.cliente_id
           WHERE c.eliminada = 0 AND c.estado = 'enviada'
             AND date(c.fecha, '+' || c.vigencia_dias || ' days') <= date('now','localtime','+5 days')
           ORDER BY vence"""
    ).fetchall()

    filas = db.execute(
        f"""SELECT c.id, c.folio, c.titulo, c.estado, c.fecha, c.total, c.vigencia_dias,
                   c.cliente_id, COALESCE(cl.nombre, 'Sin cliente') cliente,
                   CAST(julianday('now','localtime') - julianday(c.fecha) AS INTEGER) dias
            FROM cotizaciones c LEFT JOIN clientes cl ON cl.id = c.cliente_id
            WHERE c.eliminada = 0 AND c.estado IN {ABIERTAS}
            ORDER BY cl.nombre COLLATE NOCASE, c.fecha DESC"""
    ).fetchall()
    grupos = {}
    for f in filas:
        g = grupos.setdefault(f["cliente_id"], {
            "cliente_id": f["cliente_id"], "cliente": f["cliente"], "monto": 0, "mas_antigua": 0, "cotizaciones": [],
        })
        g["monto"] += f["total"]
        g["mas_antigua"] = max(g["mas_antigua"], f["dias"] or 0)
        g["cotizaciones"].append(dict(f))
    por_cliente = sorted(grupos.values(), key=lambda g: -g["monto"])

    notas = db.execute(
        """SELECT n.id, n.folio, n.fecha, COALESCE(cl.nombre,'Sin cliente') cliente,
                  (SELECT COUNT(*) FROM nota_items WHERE nota_id = n.id) partidas
           FROM notas_entrega n LEFT JOIN clientes cl ON cl.id = n.cliente_id
           WHERE n.eliminada = 0 AND n.estado = 'pendiente' ORDER BY n.fecha"""
    ).fetchall()
    stock_bajo = db.execute(
        """SELECT id, sku, nombre, stock, stock_minimo, unidad, categoria FROM inventario
           WHERE activo = 1 AND tipo = 'producto' AND stock <= stock_minimo AND stock_minimo > 0
           ORDER BY (stock - stock_minimo)"""
    ).fetchall()

    return jsonify({
        "abiertas": {"n": abiertas["n"], "monto": abiertas["monto"]},
        "aprobadas_mes": {"n": mes["n"], "monto": mes["monto"]},
        "por_vencer": [dict(r) for r in por_vencer],
        "por_cliente": por_cliente,
        "notas_pendientes": [dict(r) for r in notas],
        "stock_bajo": [dict(r) for r in stock_bajo],
    })


# =============================================================== clientes

CAMPOS_CLIENTE = ("nombre", "rfc", "contacto", "telefono", "email", "direccion", "notas")


@bp.get("/clientes")
def clientes():
    db = get_db()
    q = f"%{request.args.get('q', '').strip()}%"
    rows = db.execute(
        f"""SELECT cl.*,
              (SELECT COUNT(*) FROM cotizaciones c WHERE c.cliente_id = cl.id AND c.eliminada = 0
                 AND c.estado IN {ABIERTAS}) abiertas,
              (SELECT COALESCE(SUM(total),0) FROM cotizaciones c WHERE c.cliente_id = cl.id AND c.eliminada = 0
                 AND c.estado IN {ABIERTAS}) monto_abierto,
              (SELECT COALESCE(SUM(total),0) FROM cotizaciones c WHERE c.cliente_id = cl.id AND c.eliminada = 0
                 AND c.estado = 'aprobada') monto_aprobado,
              (SELECT MAX(fecha) FROM cotizaciones c WHERE c.cliente_id = cl.id AND c.eliminada = 0) ultima
            FROM clientes cl
            WHERE cl.nombre LIKE ? OR cl.rfc LIKE ? OR cl.contacto LIKE ?
            ORDER BY cl.nombre COLLATE NOCASE""",
        (q, q, q),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@bp.post("/clientes")
def crear_cliente():
    data = _json()
    if not _texto(data.get("nombre")):
        raise ErrorApi("El cliente necesita un nombre.")
    db = get_db()
    cur = db.execute(
        f"INSERT INTO clientes ({', '.join(CAMPOS_CLIENTE)}) VALUES ({', '.join('?' * len(CAMPOS_CLIENTE))})",
        [_texto(data.get(c)) for c in CAMPOS_CLIENTE],
    )
    db.commit()
    return jsonify(_fila(db.execute("SELECT * FROM clientes WHERE id = ?", (cur.lastrowid,)).fetchone())), 201


@bp.get("/clientes/<int:cid>")
def cliente(cid):
    db = get_db()
    _marcar_vencidas(db)
    cl = _fila(db.execute("SELECT * FROM clientes WHERE id = ?", (cid,)).fetchone())
    if not cl:
        raise ErrorApi("Cliente no encontrado.", 404)
    cl["cotizaciones"] = [dict(r) for r in db.execute(
        "SELECT id, folio, titulo, estado, fecha, total FROM cotizaciones WHERE cliente_id = ? AND eliminada = 0 ORDER BY fecha DESC, id DESC",
        (cid,))]
    cl["notas"] = [dict(r) for r in db.execute(
        "SELECT id, folio, estado, fecha FROM notas_entrega WHERE cliente_id = ? AND eliminada = 0 ORDER BY fecha DESC, id DESC",
        (cid,))]
    cl["documentos"] = [dict(r) for r in db.execute(
        "SELECT * FROM documentos WHERE cliente_id = ? ORDER BY creado DESC", (cid,))]
    return jsonify(cl)


@bp.put("/clientes/<int:cid>")
def editar_cliente(cid):
    data = _json()
    if "nombre" in data and not _texto(data.get("nombre")):
        raise ErrorApi("El cliente necesita un nombre.")
    campos = [c for c in CAMPOS_CLIENTE if c in data]
    if campos:
        db = get_db()
        db.execute(f"UPDATE clientes SET {', '.join(c + ' = ?' for c in campos)} WHERE id = ?",
                   [_texto(data[c]) for c in campos] + [cid])
        db.commit()
    return cliente(cid)


@bp.delete("/clientes/<int:cid>")
def borrar_cliente(cid):
    db = get_db()
    usado = db.execute(
        "SELECT (SELECT COUNT(*) FROM cotizaciones WHERE cliente_id = ?) + (SELECT COUNT(*) FROM notas_entrega WHERE cliente_id = ?) n",
        (cid, cid)).fetchone()["n"]
    if usado:
        raise ErrorApi("Este cliente tiene cotizaciones o notas; no se puede borrar.")
    db.execute("DELETE FROM clientes WHERE id = ?", (cid,))
    db.commit()
    return jsonify({"ok": True})


# ============================================================= inventario

CAMPOS_INV = ("sku", "nombre", "descripcion", "tipo", "categoria", "unidad", "costo", "precio", "stock_minimo", "activo")


def _validar_inv(data, parcial=False):
    if not parcial or "nombre" in data:
        if not _texto(data.get("nombre")):
            raise ErrorApi("El artículo necesita un nombre.")
    if "tipo" in data and data["tipo"] not in ("producto", "servicio"):
        raise ErrorApi("Tipo inválido.")
    if "categoria" in data and data["categoria"] not in CATEGORIAS:
        raise ErrorApi("Categoría inválida.")


def _valor_inv(campo, v):
    if campo in ("costo", "precio", "stock_minimo"):
        return _num(v)
    if campo == "activo":
        return 1 if v else 0
    return _texto(v)


@bp.get("/inventario")
def inventario():
    db = get_db()
    sql = "SELECT * FROM inventario WHERE 1=1"
    params = []
    if request.args.get("q"):
        sql += " AND (nombre LIKE ? OR sku LIKE ? OR descripcion LIKE ?)"
        params += [f"%{request.args['q']}%"] * 3
    for campo in ("tipo", "categoria"):
        if request.args.get(campo):
            sql += f" AND {campo} = ?"
            params.append(request.args[campo])
    if request.args.get("todos") != "1":
        sql += " AND activo = 1"
    sql += " ORDER BY CASE tipo WHEN 'servicio' THEN 1 ELSE 0 END, categoria, nombre COLLATE NOCASE"
    return jsonify([dict(r) for r in db.execute(sql, params)])


@bp.post("/inventario")
def crear_inv():
    data = {"tipo": "producto", "categoria": "otro", "unidad": "pza", **_json()}
    _validar_inv(data)
    db = get_db()
    campos = [c for c in CAMPOS_INV if c in data]
    cur = db.execute(
        f"INSERT INTO inventario ({', '.join(campos)}) VALUES ({', '.join('?' * len(campos))})",
        [_valor_inv(c, data[c]) for c in campos],
    )
    if data["tipo"] == "producto" and _num(data.get("stock")):
        _mover_stock(db, cur.lastrowid, "entrada", _num(data["stock"]), "Existencia inicial")
    db.commit()
    return jsonify(_fila(db.execute("SELECT * FROM inventario WHERE id = ?", (cur.lastrowid,)).fetchone())), 201


@bp.put("/inventario/<int:iid>")
def editar_inv(iid):
    data = _json()
    _validar_inv(data, parcial=True)
    campos = [c for c in CAMPOS_INV if c in data]
    db = get_db()
    if campos:
        db.execute(
            f"UPDATE inventario SET {', '.join(c + ' = ?' for c in campos)}, actualizado = datetime('now','localtime') WHERE id = ?",
            [_valor_inv(c, data[c]) for c in campos] + [iid],
        )
        db.commit()
    return jsonify(_fila(db.execute("SELECT * FROM inventario WHERE id = ?", (iid,)).fetchone()))


@bp.delete("/inventario/<int:iid>")
def borrar_inv(iid):
    db = get_db()
    usado = db.execute(
        "SELECT (SELECT COUNT(*) FROM cotizacion_items WHERE inventario_id = ?) + (SELECT COUNT(*) FROM nota_items WHERE inventario_id = ?) n",
        (iid, iid)).fetchone()["n"]
    if usado:
        # Ya aparece en documentos: se archiva en lugar de borrarse.
        db.execute("UPDATE inventario SET activo = 0 WHERE id = ?", (iid,))
        db.commit()
        return jsonify({"ok": True, "archivado": True})
    db.execute("DELETE FROM inventario WHERE id = ?", (iid,))
    db.commit()
    return jsonify({"ok": True, "archivado": False})


def _mover_stock(db, iid, tipo, cant, referencia):
    signo = {"entrada": 1, "salida": -1, "ajuste": 1}[tipo]
    db.execute("INSERT INTO movimientos (inventario_id, tipo, cantidad, referencia) VALUES (?, ?, ?, ?)",
               (iid, tipo, cant, referencia))
    db.execute("UPDATE inventario SET stock = stock + ?, actualizado = datetime('now','localtime') WHERE id = ?",
               (signo * cant, iid))


@bp.post("/inventario/<int:iid>/movimiento")
def movimiento(iid):
    data = _json()
    tipo = data.get("tipo")
    cant = _num(data.get("cantidad"))
    if tipo not in ("entrada", "salida", "ajuste") or (tipo != "ajuste" and cant <= 0):
        raise ErrorApi("Indica entrada, salida o ajuste con una cantidad válida.")
    db = get_db()
    art = db.execute("SELECT * FROM inventario WHERE id = ?", (iid,)).fetchone()
    if not art or art["tipo"] != "producto":
        raise ErrorApi("Solo los productos llevan existencias.")
    if tipo == "ajuste":
        # 'cantidad' es la existencia contada; se registra la diferencia.
        cant = cant - art["stock"]
    _mover_stock(db, iid, tipo, cant, _texto(data.get("referencia")))
    db.commit()
    return jsonify(_fila(db.execute("SELECT * FROM inventario WHERE id = ?", (iid,)).fetchone()))


@bp.get("/inventario/<int:iid>/movimientos")
def movimientos(iid):
    db = get_db()
    return jsonify([dict(r) for r in db.execute(
        "SELECT * FROM movimientos WHERE inventario_id = ? ORDER BY fecha DESC, id DESC LIMIT 100", (iid,))])


# ========================================================== cotizaciones

CAMPOS_COT = ("cliente_id", "titulo", "fecha", "vigencia_dias", "tiempo_entrega", "forma_pago",
              "condiciones", "notas_internas", "iva_pct")


def _totales(items, iva_pct):
    bruto = sum(i["cantidad"] * i["precio_unitario"] for i in items)
    desc = sum(i["cantidad"] * i["precio_unitario"] * i["descuento_pct"] / 100 for i in items)
    base = bruto - desc
    iva = round(base * iva_pct / 100, 2)
    return round(bruto, 2), round(desc, 2), iva, round(base + iva, 2)


def _cotizacion(db, cid):
    c = _fila(db.execute("SELECT * FROM cotizaciones WHERE id = ? AND eliminada = 0", (cid,)).fetchone())
    if not c:
        raise ErrorApi("Cotización no encontrada.", 404)
    c["cliente"] = _fila(db.execute("SELECT * FROM clientes WHERE id = ?", (c["cliente_id"],)).fetchone()) if c["cliente_id"] else None
    c["items"] = [dict(r) for r in db.execute(
        "SELECT * FROM cotizacion_items WHERE cotizacion_id = ? ORDER BY orden, id", (cid,))]
    c["vence"] = db.execute("SELECT date(?, '+' || ? || ' days') v", (c["fecha"], c["vigencia_dias"])).fetchone()["v"]
    c["notas"] = [dict(r) for r in db.execute(
        "SELECT id, folio, estado FROM notas_entrega WHERE cotizacion_id = ? AND eliminada = 0", (cid,))]
    c["documentos"] = [dict(r) for r in db.execute(
        "SELECT * FROM documentos WHERE tipo = 'cotizacion' AND ref_id = ? ORDER BY creado DESC", (cid,))]
    return c


def _limpiar_items(items, con_precio=True):
    limpios = []
    for n, it in enumerate(items or []):
        desc = _texto(it.get("descripcion"))
        if not desc:
            continue
        fila = {
            "inventario_id": it.get("inventario_id") or None,
            "sku": _texto(it.get("sku")),
            "descripcion": desc,
            "unidad": _texto(it.get("unidad")) or "pza",
            "cantidad": max(_num(it.get("cantidad"), 1), 0),
            "orden": n,
        }
        if con_precio:
            fila["precio_unitario"] = max(_num(it.get("precio_unitario")), 0)
            fila["descuento_pct"] = min(max(_num(it.get("descuento_pct")), 0), 100)
        limpios.append(fila)
    return limpios


def _guardar_items(db, tabla, fk, ref_id, items):
    db.execute(f"DELETE FROM {tabla} WHERE {fk} = ?", (ref_id,))
    for it in items:
        cols = [fk] + list(it.keys())
        db.execute(f"INSERT INTO {tabla} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                   [ref_id] + list(it.values()))


@bp.get("/cotizaciones")
def cotizaciones():
    db = get_db()
    _marcar_vencidas(db)
    sql = """SELECT c.id, c.folio, c.titulo, c.estado, c.fecha, c.total, c.cliente_id, c.actualizada,
                    COALESCE(cl.nombre, 'Sin cliente') cliente,
                    (SELECT COUNT(*) FROM cotizacion_items WHERE cotizacion_id = c.id) partidas
             FROM cotizaciones c LEFT JOIN clientes cl ON cl.id = c.cliente_id
             WHERE c.eliminada = 0"""
    params = []
    estado = request.args.get("estado")
    if estado == "abiertas":
        sql += f" AND c.estado IN {ABIERTAS}"
    elif estado in ESTADOS_COT:
        sql += " AND c.estado = ?"
        params.append(estado)
    if request.args.get("cliente_id"):
        sql += " AND c.cliente_id = ?"
        params.append(request.args["cliente_id"])
    if request.args.get("q"):
        sql += " AND (c.folio LIKE ? OR c.titulo LIKE ? OR cl.nombre LIKE ?)"
        params += [f"%{request.args['q']}%"] * 3
    sql += " ORDER BY c.fecha DESC, c.id DESC"
    return jsonify([dict(r) for r in db.execute(sql, params)])


@bp.post("/cotizaciones")
def crear_cotizacion():
    db = get_db()
    data = _json()
    folio = _siguiente_folio(db, "cotizaciones", config(db, "prefijo_cotizacion", "MR"))
    cur = db.execute(
        """INSERT INTO cotizaciones (folio, cliente_id, vigencia_dias, tiempo_entrega, forma_pago, condiciones, iva_pct)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (folio, data.get("cliente_id") or None, int(_num(config(db, "vigencia_dias", 15), 15)),
         config(db, "tiempo_entrega"), config(db, "forma_pago"), config(db, "condiciones"),
         _num(config(db, "iva_pct", 16), 16)),
    )
    db.commit()
    return jsonify(_cotizacion(db, cur.lastrowid)), 201


@bp.get("/cotizaciones/<int:cid>")
def cotizacion(cid):
    return jsonify(_cotizacion(get_db(), cid))


@bp.put("/cotizaciones/<int:cid>")
def guardar_cotizacion(cid):
    db = get_db()
    actual = _cotizacion(db, cid)
    data = _json()
    campos = {c: data[c] for c in CAMPOS_COT if c in data}
    if "vigencia_dias" in campos:
        campos["vigencia_dias"] = max(int(_num(campos["vigencia_dias"], 15)), 1)
    if "iva_pct" in campos:
        campos["iva_pct"] = _num(campos["iva_pct"], 16)
    if "cliente_id" in campos:
        campos["cliente_id"] = campos["cliente_id"] or None
    for k in ("titulo", "tiempo_entrega", "forma_pago", "condiciones", "notas_internas"):
        if k in campos:
            campos[k] = _texto(campos[k])
    if campos.get("fecha") is not None:
        try:
            datetime.strptime(campos["fecha"], "%Y-%m-%d")
        except ValueError:
            raise ErrorApi("Fecha inválida.")

    items = _limpiar_items(data["items"]) if "items" in data else actual["items"]
    if "items" in data:
        _guardar_items(db, "cotizacion_items", "cotizacion_id", cid, items)
    iva_pct = campos.get("iva_pct", actual["iva_pct"])
    subtotal, descuento, iva, total = _totales(items, iva_pct)
    campos.update(subtotal=subtotal, descuento=descuento, iva=iva, total=total)
    # Una vencida que se edita y se le extiende la vigencia vuelve a 'enviada'.
    db.execute(
        f"UPDATE cotizaciones SET {', '.join(k + ' = ?' for k in campos)}, actualizada = datetime('now','localtime') WHERE id = ?",
        list(campos.values()) + [cid],
    )
    db.execute(
        """UPDATE cotizaciones SET estado = 'enviada' WHERE id = ? AND estado = 'vencida'
           AND date(fecha, '+' || vigencia_dias || ' days') >= date('now','localtime')""", (cid,))
    db.commit()
    return jsonify(_cotizacion(db, cid))


@bp.post("/cotizaciones/<int:cid>/estado")
def estado_cotizacion(cid):
    estado = _json().get("estado")
    if estado not in ESTADOS_COT:
        raise ErrorApi("Estado inválido.")
    db = get_db()
    _cotizacion(db, cid)
    db.execute("UPDATE cotizaciones SET estado = ?, actualizada = datetime('now','localtime') WHERE id = ?", (estado, cid))
    db.commit()
    return jsonify(_cotizacion(db, cid))


@bp.post("/cotizaciones/<int:cid>/duplicar")
def duplicar_cotizacion(cid):
    db = get_db()
    orig = _cotizacion(db, cid)
    folio = _siguiente_folio(db, "cotizaciones", config(db, "prefijo_cotizacion", "MR"))
    campos = {c: orig[c] for c in CAMPOS_COT if c not in ("fecha",)}
    campos.update(folio=folio, subtotal=orig["subtotal"], descuento=orig["descuento"], iva=orig["iva"], total=orig["total"])
    cur = db.execute(f"INSERT INTO cotizaciones ({', '.join(campos)}) VALUES ({', '.join('?' * len(campos))})",
                     list(campos.values()))
    _guardar_items(db, "cotizacion_items", "cotizacion_id", cur.lastrowid,
                   [{k: v for k, v in it.items() if k not in ("id", "cotizacion_id")} for it in orig["items"]])
    db.commit()
    return jsonify(_cotizacion(db, cur.lastrowid)), 201


@bp.delete("/cotizaciones/<int:cid>")
def borrar_cotizacion(cid):
    db = get_db()
    db.execute("UPDATE cotizaciones SET eliminada = 1 WHERE id = ?", (cid,))
    db.commit()
    return jsonify({"ok": True})


@bp.post("/cotizaciones/<int:cid>/nota")
def nota_desde_cotizacion(cid):
    db = get_db()
    cot = _cotizacion(db, cid)
    if not cot["items"]:
        raise ErrorApi("La cotización no tiene partidas.")
    folio = _siguiente_folio(db, "notas_entrega", config(db, "prefijo_nota", "NE"))
    direccion = (cot["cliente"] or {}).get("direccion")
    cur = db.execute(
        "INSERT INTO notas_entrega (folio, cliente_id, cotizacion_id, direccion_entrega) VALUES (?, ?, ?, ?)",
        (folio, cot["cliente_id"], cid, direccion),
    )
    _guardar_items(db, "nota_items", "nota_id", cur.lastrowid, _limpiar_items(cot["items"], con_precio=False))
    db.commit()
    return jsonify(_nota(db, cur.lastrowid)), 201


# ====================================================== notas de entrega

CAMPOS_NOTA = ("cliente_id", "fecha", "direccion_entrega", "recibe", "observaciones")


def _nota(db, nid):
    n = _fila(db.execute(
        """SELECT n.*, c.folio cotizacion_folio FROM notas_entrega n
           LEFT JOIN cotizaciones c ON c.id = n.cotizacion_id WHERE n.id = ? AND n.eliminada = 0""", (nid,)).fetchone())
    if not n:
        raise ErrorApi("Nota de entrega no encontrada.", 404)
    n["cliente"] = _fila(db.execute("SELECT * FROM clientes WHERE id = ?", (n["cliente_id"],)).fetchone()) if n["cliente_id"] else None
    n["items"] = [dict(r) for r in db.execute(
        """SELECT ni.*, i.tipo, i.stock FROM nota_items ni LEFT JOIN inventario i ON i.id = ni.inventario_id
           WHERE nota_id = ? ORDER BY orden, ni.id""", (nid,))]
    n["documentos"] = [dict(r) for r in db.execute(
        "SELECT * FROM documentos WHERE tipo = 'nota' AND ref_id = ? ORDER BY creado DESC", (nid,))]
    return n


@bp.get("/notas")
def notas():
    db = get_db()
    sql = """SELECT n.id, n.folio, n.estado, n.fecha, n.cliente_id, COALESCE(cl.nombre,'Sin cliente') cliente,
                    c.folio cotizacion_folio,
                    (SELECT COUNT(*) FROM nota_items WHERE nota_id = n.id) partidas
             FROM notas_entrega n LEFT JOIN clientes cl ON cl.id = n.cliente_id
             LEFT JOIN cotizaciones c ON c.id = n.cotizacion_id
             WHERE n.eliminada = 0"""
    params = []
    if request.args.get("estado") in ("pendiente", "entregada"):
        sql += " AND n.estado = ?"
        params.append(request.args["estado"])
    if request.args.get("q"):
        sql += " AND (n.folio LIKE ? OR cl.nombre LIKE ? OR c.folio LIKE ?)"
        params += [f"%{request.args['q']}%"] * 3
    sql += " ORDER BY n.fecha DESC, n.id DESC"
    return jsonify([dict(r) for r in db.execute(sql, params)])


@bp.post("/notas")
def crear_nota():
    db = get_db()
    data = _json()
    folio = _siguiente_folio(db, "notas_entrega", config(db, "prefijo_nota", "NE"))
    cur = db.execute("INSERT INTO notas_entrega (folio, cliente_id) VALUES (?, ?)", (folio, data.get("cliente_id") or None))
    db.commit()
    return jsonify(_nota(db, cur.lastrowid)), 201


@bp.get("/notas/<int:nid>")
def nota(nid):
    return jsonify(_nota(get_db(), nid))


@bp.put("/notas/<int:nid>")
def guardar_nota(nid):
    db = get_db()
    actual = _nota(db, nid)
    data = _json()
    if actual["estado"] == "entregada" and "items" in data:
        raise ErrorApi("La nota ya se marcó como entregada; regrésala a pendiente para editar partidas.")
    campos = {c: (data[c] or None) if c == "cliente_id" else _texto(data[c]) for c in CAMPOS_NOTA if c in data}
    if campos:
        db.execute(
            f"UPDATE notas_entrega SET {', '.join(k + ' = ?' for k in campos)}, actualizada = datetime('now','localtime') WHERE id = ?",
            list(campos.values()) + [nid])
    if "items" in data:
        _guardar_items(db, "nota_items", "nota_id", nid, _limpiar_items(data["items"], con_precio=False))
    db.commit()
    return jsonify(_nota(db, nid))


@bp.post("/notas/<int:nid>/estado")
def estado_nota(nid):
    """Entregada descuenta existencias de los productos; volver a pendiente las regresa."""
    estado = _json().get("estado")
    if estado not in ("pendiente", "entregada"):
        raise ErrorApi("Estado inválido.")
    db = get_db()
    n = _nota(db, nid)
    if estado == "entregada" and not n["stock_descontado"]:
        for it in n["items"]:
            if it["inventario_id"] and it["tipo"] == "producto":
                _mover_stock(db, it["inventario_id"], "salida", it["cantidad"], f"Nota {n['folio']}")
        db.execute("UPDATE notas_entrega SET stock_descontado = 1 WHERE id = ?", (nid,))
    elif estado == "pendiente" and n["stock_descontado"]:
        for it in n["items"]:
            if it["inventario_id"] and it["tipo"] == "producto":
                _mover_stock(db, it["inventario_id"], "entrada", it["cantidad"], f"Nota {n['folio']} regresada a pendiente")
        db.execute("UPDATE notas_entrega SET stock_descontado = 0 WHERE id = ?", (nid,))
    db.execute("UPDATE notas_entrega SET estado = ?, actualizada = datetime('now','localtime') WHERE id = ?", (estado, nid))
    db.commit()
    return jsonify(_nota(db, nid))


@bp.delete("/notas/<int:nid>")
def borrar_nota(nid):
    db = get_db()
    n = _nota(db, nid)
    if n["stock_descontado"]:
        raise ErrorApi("Regresa la nota a pendiente antes de borrarla, para devolver las existencias.")
    db.execute("UPDATE notas_entrega SET eliminada = 1 WHERE id = ?", (nid,))
    db.commit()
    return jsonify({"ok": True})


# ================================================== PDFs y documentos

def _empresa(db):
    return config_todo(db)


def _pdf(tipo, rid):
    db = get_db()
    if tipo == "cotizacion":
        doc = _cotizacion(db, rid)
        return doc, pdfs.pdf_cotizacion(doc, _empresa(db), _logo())
    doc = _nota(db, rid)
    return doc, pdfs.pdf_nota(doc, _empresa(db), _logo())


def _respuesta_pdf(datos, nombre):
    return Response(datos, mimetype="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{nombre}"', "Cache-Control": "no-store"})


@bp.get("/cotizaciones/<int:cid>/vista.pdf")
def vista_cotizacion(cid):
    doc, datos = _pdf("cotizacion", cid)
    return _respuesta_pdf(datos, f"{doc['folio']}.pdf")


@bp.get("/notas/<int:nid>/vista.pdf")
def vista_nota(nid):
    doc, datos = _pdf("nota", nid)
    return _respuesta_pdf(datos, f"{doc['folio']}.pdf")


def _exportar(tipo, rid):
    """Guarda el PDF en documentos/<Cliente>/<Cotizaciones|Notas de entrega>/<Cliente> - <Folio>.pdf"""
    db = get_db()
    doc, datos = _pdf(tipo, rid)
    if not doc["cliente"]:
        raise ErrorApi("Asigna un cliente antes de exportar.")
    if not doc["items"]:
        raise ErrorApi("Agrega al menos una partida antes de exportar.")
    cliente = _nombre_seguro(doc["cliente"]["nombre"])
    sub = "Cotizaciones" if tipo == "cotizacion" else "Notas de entrega"
    carpeta = DOCS_DIR / cliente / sub
    archivo = carpeta / f"{cliente} - {doc['folio']}.pdf"
    try:
        _ruta_larga(carpeta).mkdir(parents=True, exist_ok=True)
        _ruta_larga(archivo).write_bytes(datos)
    except PermissionError:
        raise ErrorApi("No se pudo guardar: cierra el PDF si lo tienes abierto e inténtalo de nuevo.", 409)
    except OSError as e:
        raise ErrorApi(f"No se pudo guardar el PDF en {carpeta}: {e.strerror or e}", 500)
    relativo = archivo.relative_to(DOCS_DIR).as_posix()
    db.execute("DELETE FROM documentos WHERE tipo = ? AND ref_id = ? AND archivo = ?", (tipo, rid, relativo))
    db.execute("INSERT INTO documentos (tipo, ref_id, cliente_id, folio, archivo) VALUES (?, ?, ?, ?, ?)",
               (tipo, rid, doc["cliente_id"], doc["folio"], relativo))
    if tipo == "cotizacion" and doc["estado"] == "borrador":
        db.execute("UPDATE cotizaciones SET estado = 'enviada', actualizada = datetime('now','localtime') WHERE id = ?", (rid,))
    db.commit()
    doc_id = db.execute("SELECT id FROM documentos WHERE tipo = ? AND ref_id = ? AND archivo = ?",
                        (tipo, rid, relativo)).fetchone()["id"]
    return jsonify({"archivo": relativo, "url": f"/api/documentos/{doc_id}/archivo", "marcada_enviada": doc.get("estado") == "borrador"})


@bp.post("/cotizaciones/<int:cid>/exportar")
def exportar_cotizacion(cid):
    return _exportar("cotizacion", cid)


@bp.post("/notas/<int:nid>/exportar")
def exportar_nota(nid):
    return _exportar("nota", nid)


@bp.get("/documentos")
def documentos():
    db = get_db()
    sql = """SELECT d.*, COALESCE(cl.nombre,'Sin cliente') cliente FROM documentos d
             LEFT JOIN clientes cl ON cl.id = d.cliente_id WHERE 1=1"""
    params = []
    if request.args.get("cliente_id"):
        sql += " AND d.cliente_id = ?"
        params.append(request.args["cliente_id"])
    if request.args.get("q"):
        sql += " AND (d.folio LIKE ? OR cl.nombre LIKE ? OR d.archivo LIKE ?)"
        params += [f"%{request.args['q']}%"] * 3
    sql += " ORDER BY cl.nombre COLLATE NOCASE, d.creado DESC"
    rows = [dict(r) for r in db.execute(sql, params)]
    for r in rows:
        r["existe"] = _ruta_larga(DOCS_DIR / r["archivo"]).exists()
    return jsonify(rows)


def _ruta_documento(did):
    row = get_db().execute("SELECT archivo FROM documentos WHERE id = ?", (did,)).fetchone()
    if not row:
        raise ErrorApi("Documento no encontrado.", 404)
    ruta = (DOCS_DIR / row["archivo"]).resolve()
    if DOCS_DIR.resolve() not in ruta.parents or not _ruta_larga(ruta).exists():
        raise ErrorApi("El archivo ya no está en la carpeta de documentos.", 404)
    return _ruta_larga(ruta)


@bp.get("/documentos/<int:did>/archivo")
def archivo_documento(did):
    ruta = _ruta_documento(did)
    return send_file(ruta, mimetype="application/pdf", download_name=ruta.name, max_age=0)


@bp.post("/documentos/abrir-carpeta")
def abrir_carpeta():
    """Abre la carpeta del cliente (o la raíz de documentos) en el Explorador."""
    db = get_db()
    destino = DOCS_DIR
    cid = _json().get("cliente_id")
    if cid:
        cl = db.execute("SELECT nombre FROM clientes WHERE id = ?", (cid,)).fetchone()
        if cl and (DOCS_DIR / _nombre_seguro(cl["nombre"])).exists():
            destino = DOCS_DIR / _nombre_seguro(cl["nombre"])
    if sys.platform == "win32":
        os.startfile(destino)  # noqa: S606 — app local, abre el Explorador
    else:
        subprocess.Popen(["xdg-open", str(destino)])
    return jsonify({"ok": True, "ruta": str(destino)})


# ================================================================ ajustes

@bp.get("/ajustes")
def ajustes():
    datos = config_todo(get_db())
    datos["logo_personalizado"] = LOGO_SUBIDO.exists()
    return jsonify(datos)


@bp.put("/ajustes")
def guardar_ajustes():
    db = get_db()
    validas = {r["clave"] for r in db.execute("SELECT clave FROM configuracion")}
    for clave, valor in _json().items():
        if clave in validas:
            db.execute("UPDATE configuracion SET valor = ? WHERE clave = ?", ((valor or "").strip(), clave))
    db.commit()
    return ajustes()


@bp.get("/logo")
def logo():
    return send_file(_logo(), max_age=0)


@bp.post("/logo")
def subir_logo():
    f = request.files.get("logo")
    if not f:
        raise ErrorApi("Selecciona una imagen.")
    try:
        from PIL import Image
        Image.open(f.stream).convert("RGBA").save(LOGO_SUBIDO)
    except Exception:
        raise ErrorApi("No se pudo leer la imagen. Usa PNG, JPG o WEBP.")
    return ajustes()


@bp.delete("/logo")
def quitar_logo():
    LOGO_SUBIDO.unlink(missing_ok=True)
    return ajustes()
