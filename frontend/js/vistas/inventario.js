import { api, esc, dinero, num, cat, icono, vacio, toast, falla, debounce, dialogo, datosForm, confirmar, fecha, CATEGORIAS } from "../core.js";
import { contadores } from "../app.js";

const UNIDADES = ["pza", "m", "bobina", "caja", "kit", "hora", "jornada", "día", "servicio", "lote"];

export async function render(el) {
  let tipo = "";
  let categoria = "";
  let q = "";

  el.innerHTML = `
    <div class="page">
      <div class="head">
        <div class="grow"><h1>Inventario</h1><p>Productos con existencias, y servicios y personal que se cotizan por hora, jornada o servicio.</p></div>
        <div class="acciones">
          <button class="btn" id="nuevo-srv">${icono("clientes")}Servicio o personal</button>
          <button class="btn primario" id="nuevo-prod">${icono("mas")}Producto</button>
        </div>
      </div>
      <div class="barra">
        <div class="segmento" id="f-tipo" role="group" aria-label="Tipo">
          <button type="button" data-v="" aria-pressed="true">Todo</button>
          <button type="button" data-v="producto" aria-pressed="false">Productos</button>
          <button type="button" data-v="servicio" aria-pressed="false">Servicios y personal</button>
        </div>
        <div class="segmento" id="f-cat" role="group" aria-label="Categoría">
          <button type="button" data-v="" aria-pressed="true">Todas</button>
          ${Object.entries(CATEGORIAS).map(([v, t]) => `<button type="button" data-v="${v}" aria-pressed="false">${t}</button>`).join("")}
        </div>
        <input class="input buscar" type="search" placeholder="Buscar nombre o clave" aria-label="Buscar">
      </div>
      <section class="card"><div id="tabla"></div></section>
    </div>`;

  const cargar = async () => {
    const rows = await api(`/inventario?tipo=${tipo}&categoria=${categoria}&q=${encodeURIComponent(q)}`);
    el.querySelector("#tabla").innerHTML = rows.length ? `
      <div class="scroll-x"><table class="tabla">
        <thead><tr><th>Clave</th><th>Artículo</th><th>Categoría</th><th>Unidad</th><th class="der">Costo</th><th class="der">Precio</th><th class="der">Margen</th><th class="der">Existencia</th></tr></thead>
        <tbody>${rows.map((i) => {
          const margen = i.precio ? Math.round(((i.precio - i.costo) / i.precio) * 100) : null;
          const bajo = i.tipo === "producto" && i.stock_minimo > 0 && i.stock <= i.stock_minimo;
          return `<tr class="click" data-id="${i.id}">
            <td class="muted small">${esc(i.sku || "")}</td>
            <td style="font-weight:600;color:var(--ink)">${esc(i.nombre)}</td>
            <td>${cat(i.categoria)}</td>
            <td class="muted">${esc(i.unidad)}</td>
            <td class="der num muted">${dinero(i.costo)}</td>
            <td class="der num" style="font-weight:600;color:var(--ink)">${dinero(i.precio)}</td>
            <td class="der num muted">${margen === null ? "—" : margen + "%"}</td>
            <td class="der num">${i.tipo === "servicio" ? `<span class="faint">Servicio</span>` : `<span style="${bajo ? "color:var(--naranja);font-weight:700" : ""}">${num(i.stock)}</span>`}</td>
          </tr>`;
        }).join("")}</tbody>
      </table></div>`
      : vacio("Nada por aquí", q ? "Ningún artículo coincide con la búsqueda." : "Agrega productos o servicios de personal para cotizarlos rápido.");
  };

  const filtro = (sel, set) => el.querySelector(sel).addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    set(b.dataset.v);
    el.querySelectorAll(`${sel} button`).forEach((x) => x.setAttribute("aria-pressed", x === b));
    cargar();
  });
  filtro("#f-tipo", (v) => { tipo = v; });
  filtro("#f-cat", (v) => { categoria = v; });
  el.querySelector(".buscar").addEventListener("input", debounce((e) => { q = e.target.value.trim(); cargar(); }, 200));
  el.querySelector("#nuevo-prod").onclick = () => editar({ tipo: "producto", categoria: "cctv", unidad: "pza" }, cargar);
  el.querySelector("#nuevo-srv").onclick = () => editar({ tipo: "servicio", categoria: "personal", unidad: "jornada" }, cargar);
  el.querySelector("#tabla").addEventListener("click", async (e) => {
    const tr = e.target.closest("tr[data-id]");
    if (!tr) return;
    const rows = await api("/inventario?todos=1");
    editar(rows.find((r) => r.id === +tr.dataset.id), cargar);
  });
  await cargar();
}

function editar(art, recargar) {
  const nuevo = !art.id;
  const producto = art.tipo === "producto";
  const d = dialogo({
    titulo: nuevo ? (producto ? "Nuevo producto" : "Nuevo servicio o personal") : art.nombre,
    aceptar: nuevo ? "Agregar" : "Guardar",
    cuerpo: `
      <div class="rejilla" style="grid-template-columns:repeat(auto-fill,minmax(150px,1fr))">
        <label class="campo ancho">Nombre<input class="input" name="nombre" required value="${esc(art.nombre)}" placeholder="${producto ? "Ej. Cámara domo 2 MP" : "Ej. Técnico instalador"}"></label>
        <label class="campo">Clave<input class="input" name="sku" value="${esc(art.sku)}"></label>
        <label class="campo">Tipo<select class="input" name="tipo">
          <option value="producto" ${producto ? "selected" : ""}>Producto</option>
          <option value="servicio" ${!producto ? "selected" : ""}>Servicio / personal</option></select></label>
        <label class="campo">Categoría<select class="input" name="categoria">
          ${Object.entries(CATEGORIAS).map(([v, t]) => `<option value="${v}" ${art.categoria === v ? "selected" : ""}>${t}</option>`).join("")}</select></label>
        <label class="campo">Unidad<input class="input" name="unidad" list="unidades" value="${esc(art.unidad)}"></label>
        <label class="campo">Costo<input class="input" name="costo" inputmode="decimal" value="${art.costo ?? 0}"></label>
        <label class="campo">Precio de venta<input class="input" name="precio" inputmode="decimal" value="${art.precio ?? 0}"></label>
        <label class="campo" data-prod>Stock mínimo<input class="input" name="stock_minimo" inputmode="decimal" value="${art.stock_minimo ?? 0}"></label>
        ${nuevo ? `<label class="campo" data-prod>Existencia inicial<input class="input" name="stock" inputmode="decimal" value="0"></label>` : ""}
        <label class="campo ancho">Descripción (interna)<input class="input" name="descripcion" value="${esc(art.descripcion)}"></label>
      </div>
      <datalist id="unidades">${UNIDADES.map((u) => `<option value="${u}">`).join("")}</datalist>
      ${!nuevo && producto ? `
        <div style="margin-top:18px;padding-top:14px;border-top:1px solid var(--line)">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
            <h2 style="flex:1">Existencia: <span class="num">${num(art.stock)} ${esc(art.unidad)}</span></h2>
            <button type="button" class="btn chico" data-mov="entrada">Entrada</button>
            <button type="button" class="btn chico" data-mov="salida">Salida</button>
            <button type="button" class="btn chico" data-mov="ajuste">Ajustar conteo</button>
          </div>
          <div id="movs" class="small muted">Cargando movimientos…</div>
        </div>` : ""}`,
    alAceptar: async (form) => {
      const datos = datosForm(form);
      if (nuevo) await api("/inventario", { method: "POST", body: datos });
      else await api(`/inventario/${art.id}`, { method: "PUT", body: datos });
      toast(nuevo ? "Artículo agregado" : "Artículo guardado");
      recargar();
      contadores();
    },
  });

  const tipoSel = d.querySelector('[name="tipo"]');
  const sincronizar = () => d.querySelectorAll("[data-prod]").forEach((x) => { x.hidden = tipoSel.value !== "producto"; });
  tipoSel.addEventListener("change", sincronizar);
  sincronizar();

  if (!nuevo) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "btn fantasma peligro";
    b.style.marginRight = "auto";
    b.textContent = "Quitar del inventario";
    b.onclick = async () => {
      if (!await confirmar("Quitar artículo", `<b>${esc(art.nombre)}</b> dejará de aparecer al cotizar. Si ya está en documentos, se archiva en lugar de borrarse.`, "Quitar")) return;
      try {
        const r = await api(`/inventario/${art.id}`, { method: "DELETE" });
        toast(r.archivado ? "Artículo archivado" : "Artículo borrado");
        d.close();
        recargar();
      } catch (e) { falla(e); }
    };
    d.querySelector("footer").prepend(b);
  }

  if (!nuevo && producto) {
    api(`/inventario/${art.id}/movimientos`).then((movs) => {
      d.querySelector("#movs").innerHTML = movs.length ? `<table class="tabla"><tbody>${movs.slice(0, 8).map((m) => {
        const v = m.tipo === "salida" ? -m.cantidad : m.cantidad;
        return `<tr><td>${fecha(m.fecha, true)}</td><td>${m.tipo}</td><td class="der num" style="color:var(--ink)">${v > 0 ? "+" : ""}${num(v)}</td><td>${esc(m.referencia || "")}</td></tr>`;
      }).join("")}</tbody></table>`
        : "Sin movimientos todavía.";
    });
    d.querySelectorAll("[data-mov]").forEach((btn) => btn.addEventListener("click", () => {
      const tipo = btn.dataset.mov;
      dialogo({
        titulo: { entrada: "Entrada de material", salida: "Salida de material", ajuste: "Ajustar al conteo físico" }[tipo],
        aceptar: "Registrar",
        cuerpo: `<div class="rejilla">
          <label class="campo">${tipo === "ajuste" ? "Existencia contada" : "Cantidad"}<input class="input" name="cantidad" inputmode="decimal" required></label>
          <label class="campo">Referencia<input class="input" name="referencia" placeholder="${tipo === "entrada" ? "Factura o proveedor" : "Motivo"}"></label></div>`,
        alAceptar: async (form) => {
          await api(`/inventario/${art.id}/movimiento`, { method: "POST", body: { tipo, ...datosForm(form) } });
          toast("Movimiento registrado");
          d.close();
          recargar();
          contadores();
        },
      });
    }));
  }
}
