// Piezas compartidas entre vistas: crear documentos, alta rápida de cliente,
// selector de cliente y la tabla de partidas con búsqueda en inventario.
import { api, esc, dinero, num, cat, icono, dialogo, datosForm, falla } from "../core.js";

export async function nuevaCotizacion(cliente_id = null) {
  try {
    const c = await api("/cotizaciones", { method: "POST", body: { cliente_id } });
    location.hash = `#/cotizacion/${c.id}`;
  } catch (e) { falla(e); }
}

export async function nuevaNota(cliente_id = null) {
  try {
    const n = await api("/notas", { method: "POST", body: { cliente_id } });
    location.hash = `#/nota/${n.id}`;
  } catch (e) { falla(e); }
}

export const camposCliente = (c = {}) => `
  <div class="rejilla">
    <label class="campo ancho">Nombre o razón social<input class="input" name="nombre" required value="${esc(c.nombre)}"></label>
    <label class="campo">Contacto<input class="input" name="contacto" value="${esc(c.contacto)}"></label>
    <label class="campo">RFC<input class="input" name="rfc" value="${esc(c.rfc)}"></label>
    <label class="campo">Teléfono<input class="input" name="telefono" value="${esc(c.telefono)}"></label>
    <label class="campo">Correo<input class="input" name="email" type="email" value="${esc(c.email)}"></label>
    <label class="campo ancho">Dirección<input class="input" name="direccion" value="${esc(c.direccion)}"></label>
  </div>`;

export function clienteRapido(nombre = "") {
  return new Promise((ok) => {
    let creado = null;
    const d = dialogo({
      titulo: "Nuevo cliente", aceptar: "Crear cliente", cuerpo: camposCliente({ nombre }),
      alAceptar: async (form) => { creado = await api("/clientes", { method: "POST", body: datosForm(form) }); },
    });
    d.addEventListener("close", () => ok(creado));
  });
}

// ------------------------------------------------------------ selector de cliente

export function selectorCliente(contenedor, actual, alCambiar) {
  contenedor.innerHTML = `
    <div class="combo">
      <input class="input" placeholder="Busca o crea un cliente" autocomplete="off" value="${esc(actual?.nombre)}" aria-label="Cliente">
      <div class="sugerencias" hidden role="listbox"></div>
    </div>`;
  const input = contenedor.querySelector("input");
  const caja = contenedor.querySelector(".sugerencias");
  let opciones = [];
  let sel = 0;

  const pintar = () => {
    caja.innerHTML = opciones.map((o, i) => `
      <button type="button" role="option" aria-selected="${i === sel}" data-i="${i}">
        <span class="n">${o.nuevo ? `${icono("mas")} Crear “${esc(o.nombre)}”` : esc(o.nombre)}</span>
        <span class="p small">${o.abiertas ? `${o.abiertas} abiertas` : ""}</span>
        ${o.contacto ? `<span class="m">${esc(o.contacto)}</span>` : ""}
      </button>`).join("");
    caja.hidden = !opciones.length;
  };

  const elegir = async (o) => {
    caja.hidden = true;
    if (o.nuevo) {
      const c = await clienteRapido(o.nombre);
      if (!c) { input.value = actual?.nombre || ""; return; }
      o = c;
    }
    actual = o;
    input.value = o.nombre;
    alCambiar(o);
  };

  const buscar = async () => {
    const q = input.value.trim();
    const lista = await api(`/clientes?q=${encodeURIComponent(q)}`);
    opciones = lista.slice(0, 8);
    if (q && !lista.some((c) => c.nombre.toLowerCase() === q.toLowerCase())) opciones.push({ nuevo: true, nombre: q });
    sel = 0;
    pintar();
  };

  input.addEventListener("focus", () => { input.select(); buscar(); });
  input.addEventListener("input", buscar);
  input.addEventListener("keydown", (e) => {
    if (caja.hidden) return;
    if (e.key === "ArrowDown") { sel = Math.min(sel + 1, opciones.length - 1); pintar(); e.preventDefault(); }
    if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); pintar(); e.preventDefault(); }
    if (e.key === "Enter" && opciones[sel]) { e.preventDefault(); elegir(opciones[sel]); }
    if (e.key === "Escape") { caja.hidden = true; input.value = actual?.nombre || ""; }
  });
  input.addEventListener("blur", () => setTimeout(() => {
    caja.hidden = true;
    if (!input.value.trim() && actual) { actual = null; alCambiar(null); }
    else input.value = actual?.nombre || "";
  }, 160));
  caja.addEventListener("mousedown", (e) => e.preventDefault());
  caja.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) elegir(opciones[+b.dataset.i]);
  });
}

// ------------------------------------------------------------ partidas

/**
 * Tabla editable de partidas.
 * conPrecio: true en cotizaciones (precio, descuento, importe); false en notas
 * (muestra existencias disponibles en su lugar).
 */
export async function tablaPartidas(contenedor, items, { conPrecio, alCambiar, bloqueado = false }) {
  const inventario = await api("/inventario");
  const porId = () => Object.fromEntries(inventario.map((i) => [i.id, i]));

  contenedor.innerHTML = `
    ${bloqueado ? "" : `<div class="agregar">
      ${icono("buscar")}
      <input class="input" placeholder="Agregar del inventario: escribe nombre o clave y presiona Enter" autocomplete="off" aria-label="Buscar en inventario">
      <button type="button" class="btn" data-libre>${icono("mas")}Partida libre</button>
      <div class="sugerencias" hidden role="listbox"></div>
    </div>`}
    <div class="scroll-x"><table class="partidas">
      <thead><tr>
        <th>#</th><th>Descripción</th><th class="der" style="width:70px">Cant.</th><th style="width:86px">Unidad</th>
        ${conPrecio ? `<th class="der" style="width:104px">P. unitario</th><th class="der" style="width:64px">Desc. %</th><th class="der" style="width:112px">Importe</th>` : `<th style="width:120px">Existencia</th>`}
        <th style="width:46px"></th>
      </tr></thead>
      <tbody></tbody>
    </table></div>`;

  const tbody = contenedor.querySelector("tbody");

  const fila = (it, i) => {
    const art = it.inventario_id ? porId()[it.inventario_id] : null;
    const importe = it.cantidad * it.precio_unitario * (1 - (it.descuento_pct || 0) / 100);
    let existencia = "";
    if (!conPrecio) {
      if (art?.tipo === "producto") existencia = `<span class="stock ${art.stock < it.cantidad ? "falta" : ""}">${num(art.stock)} disponibles</span>`;
      else if (art) existencia = `<span class="stock">Servicio</span>`;
    }
    const dis = bloqueado ? "disabled" : "";
    return `<tr data-i="${i}">
      <td class="n">${i + 1}</td>
      <td><input class="celda" data-k="descripcion" value="${esc(it.descripcion)}" ${dis} aria-label="Descripción">${it.sku ? `<span class="sku">${esc(it.sku)}</span>` : ""}</td>
      <td><input class="celda der" data-k="cantidad" inputmode="decimal" value="${it.cantidad}" ${dis} aria-label="Cantidad"></td>
      <td><input class="celda" data-k="unidad" value="${esc(it.unidad)}" ${dis} aria-label="Unidad"></td>
      ${conPrecio ? `
        <td><input class="celda der" data-k="precio_unitario" inputmode="decimal" value="${it.precio_unitario}" ${dis} aria-label="Precio unitario"></td>
        <td><input class="celda der" data-k="descuento_pct" inputmode="decimal" value="${it.descuento_pct || 0}" ${dis} aria-label="Descuento"></td>
        <td class="importe">${dinero(importe)}</td>` : `<td>${existencia}</td>`}
      <td>${bloqueado ? "" : `<button type="button" class="btn fantasma icono chico quitar" data-quitar aria-label="Quitar partida">${icono("x")}</button>`}</td>
    </tr>`;
  };

  const pintar = () => {
    tbody.innerHTML = items.length ? items.map(fila).join("")
      : `<tr><td colspan="8" class="vacio" style="padding-left:18px"><b>Sin partidas todavía</b>Busca arriba un producto, servicio o personal del inventario, o agrega una partida libre.</td></tr>`;
  };
  pintar();

  tbody.addEventListener("input", (e) => {
    const k = e.target.dataset.k;
    if (!k) return;
    const i = +e.target.closest("tr").dataset.i;
    items[i][k] = ["cantidad", "precio_unitario", "descuento_pct"].includes(k) ? parseFloat(e.target.value.replace(/[$,\s]/g, "")) || 0 : e.target.value;
    if (conPrecio) {
      const it = items[i];
      e.target.closest("tr").querySelector(".importe").textContent = dinero(it.cantidad * it.precio_unitario * (1 - it.descuento_pct / 100));
    }
    alCambiar(items);
  });
  tbody.addEventListener("change", (e) => { if (!conPrecio && e.target.dataset.k === "cantidad") pintar(); });
  tbody.addEventListener("focusin", (e) => { if (e.target.classList.contains("celda")) e.target.select(); });
  tbody.addEventListener("keydown", (e) => {
    // Enter baja a la misma columna de la siguiente fila, como en una hoja de cálculo.
    if (e.key !== "Enter" || !e.target.dataset.k) return;
    e.preventDefault();
    const sig = e.target.closest("tr").nextElementSibling?.querySelector(`[data-k="${e.target.dataset.k}"]`);
    (sig || contenedor.querySelector(".agregar input"))?.focus();
  });
  tbody.addEventListener("click", (e) => {
    if (!e.target.closest("[data-quitar]")) return;
    items.splice(+e.target.closest("tr").dataset.i, 1);
    pintar();
    alCambiar(items);
  });

  if (bloqueado) return { inventario: porId };

  const input = contenedor.querySelector(".agregar input");
  const caja = contenedor.querySelector(".agregar .sugerencias");
  let opciones = [];
  let sel = 0;

  const pintarOpciones = () => {
    caja.innerHTML = opciones.map((o, i) => `
      <button type="button" role="option" aria-selected="${i === sel}" data-i="${i}">
        <span class="n">${esc(o.nombre)}</span>
        <span class="p">${conPrecio ? dinero(o.precio) : (o.tipo === "producto" ? `${num(o.stock)} disp.` : "")}</span>
        <span class="m">${cat(o.categoria)}${o.sku ? `<span>${esc(o.sku)}</span>` : ""}<span>por ${esc(o.unidad)}</span>${o.tipo === "producto" && conPrecio ? `<span>${num(o.stock)} en stock</span>` : ""}</span>
      </button>`).join("") || `<div class="muted small" style="padding:10px">Nada coincide. Usa “Partida libre” o da de alta el artículo en Inventario.</div>`;
    caja.hidden = false;
  };

  const filtrar = () => {
    const q = input.value.trim().toLowerCase();
    opciones = inventario.filter((o) => !q || `${o.nombre} ${o.sku || ""} ${o.descripcion || ""}`.toLowerCase().includes(q)).slice(0, 10);
    sel = 0;
    pintarOpciones();
  };

  const agregar = (o) => {
    const existente = items.findIndex((it) => it.inventario_id === o.id);
    if (existente >= 0) items[existente].cantidad += 1;
    else items.push({
      inventario_id: o.id, sku: o.sku, descripcion: o.nombre, unidad: o.unidad, cantidad: 1,
      precio_unitario: o.precio, descuento_pct: 0,
    });
    pintar();
    alCambiar(items);
    input.value = "";
    caja.hidden = true;
    // Deja el cursor en la cantidad de la partida para ajustarla al momento.
    const i = existente >= 0 ? existente : items.length - 1;
    tbody.querySelector(`tr[data-i="${i}"] [data-k="cantidad"]`)?.focus();
  };

  input.addEventListener("focus", filtrar);
  input.addEventListener("input", filtrar);
  input.addEventListener("blur", () => setTimeout(() => { caja.hidden = true; }, 160));
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { sel = Math.min(sel + 1, opciones.length - 1); pintarOpciones(); e.preventDefault(); }
    if (e.key === "ArrowUp") { sel = Math.max(sel - 1, 0); pintarOpciones(); e.preventDefault(); }
    if (e.key === "Enter" && opciones[sel]) { e.preventDefault(); agregar(opciones[sel]); }
    if (e.key === "Escape") { caja.hidden = true; input.blur(); }
  });
  caja.addEventListener("mousedown", (e) => e.preventDefault());
  caja.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) agregar(opciones[+b.dataset.i]);
  });
  contenedor.querySelector("[data-libre]").addEventListener("click", () => {
    items.push({ inventario_id: null, sku: null, descripcion: input.value.trim() || "", unidad: "servicio", cantidad: 1, precio_unitario: 0, descuento_pct: 0 });
    input.value = "";
    pintar();
    tbody.querySelector(`tr[data-i="${items.length - 1}"] [data-k="descripcion"]`)?.focus();
  });

  return { inventario: porId };
}
