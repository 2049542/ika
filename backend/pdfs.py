"""
PDFs de cotización y nota de entrega (reportlab, sin navegador).

Ambos comparten encabezado: logo MR a la izquierda, tipo de documento y folio
a la derecha, y la franja de tres colores del logo (naranja, verde, azul)
como firma visual. Se generan en memoria (bytes): la vista previa los manda
directo al navegador y la exportación los guarda en /documentos/<cliente>/.
"""
import io
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import (
    KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

TINTA = colors.HexColor("#141821")
TEXTO = colors.HexColor("#3A404C")
TENUE = colors.HexColor("#7A818E")
LINEA = colors.HexColor("#E3E6EB")
FONDO = colors.HexColor("#F4F5F7")
NARANJA = colors.HexColor("#F29A1F")
VERDE = colors.HexColor("#4DB034")
AZUL = colors.HexColor("#1F7FD6")

MARGEN = 18 * mm
ALTO_HEADER = 38 * mm


def _registrar_fuentes():
    """Segoe UI si está en Windows; si no, Helvetica."""
    fuentes = Path("C:/Windows/Fonts")
    archivos = {"IKA": "segoeui.ttf", "IKA-Semi": "seguisb.ttf", "IKA-Bold": "segoeuib.ttf"}
    try:
        for nombre, archivo in archivos.items():
            pdfmetrics.registerFont(TTFont(nombre, str(fuentes / archivo)))
        return "IKA", "IKA-Semi", "IKA-Bold"
    except Exception:
        return "Helvetica", "Helvetica-Bold", "Helvetica-Bold"


F_REG, F_SEMI, F_BOLD = _registrar_fuentes()


def dinero(v) -> str:
    return f"${(v or 0):,.2f}"


def cantidad(v) -> str:
    return f"{v:,.2f}".rstrip("0").rstrip(".") if v is not None else ""


def _estilos():
    base = dict(fontName=F_REG, fontSize=9, leading=12.5, textColor=TEXTO)
    return {
        "normal": ParagraphStyle("n", **base),
        "tenue": ParagraphStyle("t", **{**base, "textColor": TENUE, "fontSize": 8, "leading": 11}),
        "etiqueta": ParagraphStyle("e", **{**base, "fontName": F_SEMI, "textColor": TENUE, "fontSize": 7.5, "leading": 10}),
        "fuerte": ParagraphStyle("f", **{**base, "fontName": F_SEMI, "textColor": TINTA, "fontSize": 10.5, "leading": 14}),
        "titulo": ParagraphStyle("ti", **{**base, "fontName": F_BOLD, "textColor": TINTA, "fontSize": 13, "leading": 17}),
        "celda": ParagraphStyle("c", **{**base, "fontSize": 8.5, "leading": 11.5}),
        "celda_der": ParagraphStyle("cd", **{**base, "fontSize": 8.5, "leading": 11.5, "alignment": 2}),
        "th": ParagraphStyle("th", **{**base, "fontName": F_SEMI, "fontSize": 7.5, "textColor": TENUE}),
        "th_der": ParagraphStyle("thd", **{**base, "fontName": F_SEMI, "fontSize": 7.5, "textColor": TENUE, "alignment": 2}),
    }


def _esc(texto) -> str:
    return (str(texto or "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")


class _CanvasNumerado(pdfcanvas.Canvas):
    """Canvas en dos pasadas para poder escribir 'Página x de y'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._paginas = []

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._paginas)
        for estado in self._paginas:
            self.__dict__.update(estado)
            self.setFont(F_REG, 7.5)
            self.setFillColor(TENUE)
            self.drawRightString(letter[0] - MARGEN, 10 * mm, f"Página {self._pageNumber} de {total}")
            super().showPage()
        super().save()


def _dibujar_marco(c, empresa, logo, tipo_doc, folio, meta):
    ancho, alto = letter
    c.saveState()

    # Logo
    tope = alto - 12 * mm
    if logo and Path(logo).exists():
        try:
            img = ImageReader(str(logo))
            iw, ih = img.getSize()
            h = 22 * mm
            c.drawImage(img, MARGEN, tope - h, width=h * iw / ih, height=h, mask="auto")
        except Exception:
            logo = None
    if not logo:
        c.setFont(F_BOLD, 18)
        c.setFillColor(TINTA)
        c.drawString(MARGEN, tope - 10 * mm, empresa.get("empresa_nombre", ""))

    # Tipo de documento + folio
    x = ancho - MARGEN
    c.setFillColor(TENUE)
    c.setFont(F_SEMI, 8)
    c.drawRightString(x, tope - 3 * mm, tipo_doc.upper())
    c.setFillColor(TINTA)
    c.setFont(F_BOLD, 17)
    c.drawRightString(x, tope - 10.5 * mm, folio)
    c.setFont(F_REG, 8.5)
    c.setFillColor(TEXTO)
    y = tope - 16 * mm
    for etiqueta, valor in meta:
        c.drawRightString(x, y, f"{etiqueta}  {valor}")
        y -= 4.2 * mm

    # Franja de tres colores del logo
    y_franja = alto - ALTO_HEADER + 2 * mm
    w = (ancho - 2 * MARGEN) / 3
    for i, col in enumerate((NARANJA, VERDE, AZUL)):
        c.setFillColor(col)
        c.rect(MARGEN + i * w, y_franja, w, 1.1 * mm, stroke=0, fill=1)

    # Pie
    partes = [empresa.get(k, "") for k in ("empresa_nombre", "empresa_telefono", "empresa_email", "empresa_web")]
    c.setFont(F_REG, 7.5)
    c.setFillColor(TENUE)
    c.drawString(MARGEN, 10 * mm, "   |   ".join(p for p in partes if p))
    c.setStrokeColor(LINEA)
    c.setLineWidth(0.5)
    c.line(MARGEN, 14 * mm, ancho - MARGEN, 14 * mm)
    c.restoreState()


def _bloque_partes(cliente, empresa, est, extra_cliente=None):
    """Dos columnas: Para (cliente) / De (empresa)."""
    def lineas(*vals):
        return "<br/>".join(_esc(v) for v in vals if v)

    para = [Paragraph("PARA", est["etiqueta"]), Spacer(1, 1.5 * mm),
            Paragraph(_esc(cliente.get("nombre") or "Sin cliente"), est["fuerte"]),
            Paragraph(lineas(
                cliente.get("contacto") and f"Atención: {cliente['contacto']}",
                cliente.get("rfc") and f"RFC: {cliente['rfc']}",
                cliente.get("direccion"), cliente.get("telefono"), cliente.get("email"),
                *(extra_cliente or []),
            ), est["normal"])]
    de = [Paragraph("DE", est["etiqueta"]), Spacer(1, 1.5 * mm),
          Paragraph(_esc(empresa.get("empresa_nombre")), est["fuerte"]),
          Paragraph(lineas(
              empresa.get("empresa_lema"),
              empresa.get("empresa_rfc") and f"RFC: {empresa['empresa_rfc']}",
              empresa.get("empresa_direccion"), empresa.get("empresa_telefono"), empresa.get("empresa_email"),
          ), est["normal"])]
    t = Table([[para, de]], colWidths=[(letter[0] - 2 * MARGEN) * 0.55, (letter[0] - 2 * MARGEN) * 0.45])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6 * mm),
    ]))
    return t


def _estilo_tabla():
    estilo = [
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, TINTA),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINEA),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]
    return TableStyle(estilo)


def _descripcion(it, est):
    txt = _esc(it["descripcion"])
    if it.get("sku"):
        txt += f'<br/><font size="7" color="#7A818E">{_esc(it["sku"])}</font>'
    return Paragraph(txt, est["celda"])


def _construir(story, empresa, logo, tipo_doc, folio, meta) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter, title=f"{tipo_doc} {folio}", author=empresa.get("empresa_nombre", ""),
        topMargin=ALTO_HEADER + 4 * mm, bottomMargin=22 * mm, leftMargin=MARGEN, rightMargin=MARGEN,
    )
    marco = lambda c, d: _dibujar_marco(c, empresa, logo, tipo_doc, folio, meta)
    doc.build(story, onFirstPage=marco, onLaterPages=marco, canvasmaker=_CanvasNumerado)
    return buf.getvalue()


def _firma(etiqueta, nombre, puesto, est, ancho):
    return Table(
        [[""], [Paragraph(etiqueta, est["etiqueta"])], [Paragraph(_esc(nombre), est["normal"])], [Paragraph(_esc(puesto), est["tenue"])]],
        colWidths=[ancho], rowHeights=[14 * mm, None, None, None],
        style=TableStyle([
            ("LINEBELOW", (0, 0), (0, 0), 0.6, TINTA),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 1), (-1, -1), 1.5),
        ]),
    )


# ------------------------------------------------------------- cotización

def pdf_cotizacion(cot: dict, empresa: dict, logo) -> bytes:
    est = _estilos()
    cliente = cot.get("cliente") or {}
    ancho_util = letter[0] - 2 * MARGEN
    story = [_bloque_partes(cliente, empresa, est), Spacer(1, 7 * mm)]

    if cot.get("titulo"):
        story += [Paragraph(_esc(cot["titulo"]), est["titulo"]), Spacer(1, 3 * mm)]

    hay_desc = any(it["descuento_pct"] for it in cot["items"])
    enc = ["#", "Descripción", "Cant.", "Unidad", "P. unitario"] + (["Desc."] if hay_desc else []) + ["Importe"]
    filas = [[Paragraph(h, est["th_der"] if i >= 2 and h not in ("Unidad",) else est["th"]) for i, h in enumerate(enc)]]
    for n, it in enumerate(cot["items"], 1):
        importe = it["cantidad"] * it["precio_unitario"] * (1 - it["descuento_pct"] / 100)
        fila = [
            Paragraph(str(n), est["tenue"]), _descripcion(it, est),
            Paragraph(cantidad(it["cantidad"]), est["celda_der"]), Paragraph(_esc(it["unidad"]), est["celda"]),
            Paragraph(dinero(it["precio_unitario"]), est["celda_der"]),
        ]
        if hay_desc:
            fila.append(Paragraph(f"{cantidad(it['descuento_pct'])}%" if it["descuento_pct"] else "", est["celda_der"]))
        fila.append(Paragraph(dinero(importe), est["celda_der"]))
        filas.append(fila)

    fijos = [8 * mm, None, 15 * mm, 17 * mm, 25 * mm] + ([14 * mm] if hay_desc else []) + [27 * mm]
    fijos[1] = ancho_util - sum(w for w in fijos if w)
    tabla = Table(filas, colWidths=fijos, repeatRows=1)
    tabla.setStyle(_estilo_tabla())
    story += [tabla, Spacer(1, 5 * mm)]

    # Totales
    tot = [["Subtotal", dinero(cot["subtotal"])]]
    if cot["descuento"]:
        tot.append(["Descuento", f"-{dinero(cot['descuento'])}"])
    tot.append([f"IVA {cantidad(cot['iva_pct'])}%", dinero(cot["iva"])])
    tot_rows = [[Paragraph(a, est["celda_der"]), Paragraph(b, est["celda_der"])] for a, b in tot]
    tot_rows.append([
        Paragraph("Total MXN", ParagraphStyle("tl", parent=est["celda_der"], fontName=F_SEMI, textColor=TINTA, fontSize=10)),
        Paragraph(dinero(cot["total"]), ParagraphStyle("tv", parent=est["celda_der"], fontName=F_BOLD, textColor=TINTA, fontSize=13, leading=16)),
    ])
    t_tot = Table(tot_rows, colWidths=[32 * mm, 34 * mm], hAlign="RIGHT")
    t_tot.setStyle(TableStyle([
        ("LINEABOVE", (0, len(tot_rows) - 1), (-1, len(tot_rows) - 1), 0.8, TINTA),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("TOPPADDING", (0, len(tot_rows) - 1), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [KeepTogether(t_tot), Spacer(1, 8 * mm)]

    # Condiciones comerciales
    cond = []
    for etiqueta, valor in (
        ("Tiempo de entrega", cot.get("tiempo_entrega")),
        ("Forma de pago", cot.get("forma_pago")),
        ("Vigencia", f"{cot['vigencia_dias']} días a partir del {cot['fecha']}"),
    ):
        if valor:
            cond.append([Paragraph(etiqueta, est["etiqueta"]), Paragraph(_esc(valor), est["normal"])])
    bloque = [Paragraph("CONDICIONES COMERCIALES", est["etiqueta"]), Spacer(1, 2 * mm)]
    if cond:
        t_cond = Table(cond, colWidths=[34 * mm, ancho_util - 34 * mm])
        t_cond.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 1.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        bloque.append(t_cond)
    if cot.get("condiciones"):
        bloque += [Spacer(1, 2.5 * mm), Paragraph(_esc(cot["condiciones"]), est["tenue"])]
    story.append(KeepTogether(bloque))

    if empresa.get("firma_nombre"):
        story += [Spacer(1, 12 * mm), _firma("ATENTAMENTE", empresa["firma_nombre"], empresa.get("firma_puesto"), est, 70 * mm)]

    meta = [("Fecha", cot["fecha"]), ("Vigencia", f"{cot['vigencia_dias']} días")]
    return _construir(story, empresa, logo, "Cotización", cot["folio"], meta)


# ------------------------------------------------------- nota de entrega

def pdf_nota(nota: dict, empresa: dict, logo) -> bytes:
    est = _estilos()
    cliente = nota.get("cliente") or {}
    ancho_util = letter[0] - 2 * MARGEN
    extra = []
    if nota.get("direccion_entrega") and nota["direccion_entrega"] != cliente.get("direccion"):
        extra.append(f"Entregar en: {nota['direccion_entrega']}")
    story = [_bloque_partes(cliente, empresa, est, extra), Spacer(1, 7 * mm)]

    enc = ["#", "Descripción", "Cant.", "Unidad", "Recibido"]
    filas = [[Paragraph(h, est["th_der"] if h == "Cant." else est["th"]) for h in enc]]
    for n, it in enumerate(nota["items"], 1):
        filas.append([
            Paragraph(str(n), est["tenue"]), _descripcion(it, est),
            Paragraph(cantidad(it["cantidad"]), est["celda_der"]), Paragraph(_esc(it["unidad"]), est["celda"]),
            "",
        ])
    cols = [8 * mm, None, 18 * mm, 22 * mm, 17 * mm]
    cols[1] = ancho_util - sum(w for w in cols if w)
    tabla = Table(filas, colWidths=cols, repeatRows=1)
    estilo = _estilo_tabla()
    # Casilla para palomear lo recibido
    for r in range(1, len(filas)):
        estilo.add("BOX", (4, r), (4, r), 0.6, TENUE)
    tabla.setStyle(estilo)
    total_piezas = sum(it["cantidad"] for it in nota["items"])
    story += [tabla, Spacer(1, 3 * mm),
              Paragraph(f"{len(nota['items'])} partidas  |  {cantidad(total_piezas)} unidades en total", est["tenue"]),
              Spacer(1, 7 * mm)]

    if nota.get("observaciones"):
        story += [Paragraph("OBSERVACIONES", est["etiqueta"]), Spacer(1, 1.5 * mm),
                  Paragraph(_esc(nota["observaciones"]), est["normal"]), Spacer(1, 6 * mm)]

    story.append(Paragraph(
        "El cliente declara recibir los materiales y/o servicios descritos en buen estado y a su entera satisfacción.",
        est["tenue"]))
    story.append(Spacer(1, 14 * mm))
    mitad = (ancho_util - 14 * mm) / 2
    firmas = Table([[
        _firma("ENTREGA", empresa.get("firma_nombre") or empresa.get("empresa_nombre"), empresa.get("firma_puesto") or "", est, mitad),
        _firma("RECIBE  (nombre, firma y fecha)", nota.get("recibe") or "", "", est, mitad),
    ]], colWidths=[mitad + 14 * mm, mitad])
    firmas.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(KeepTogether(firmas))

    meta = [("Fecha", nota["fecha"])]
    if nota.get("cotizacion_folio"):
        meta.append(("Ref. cotización", nota["cotizacion_folio"]))
    return _construir(story, empresa, logo, "Nota de entrega", nota["folio"], meta)
