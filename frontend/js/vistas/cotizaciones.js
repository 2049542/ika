import {
  api, esc, dinero, fecha, pill, icono, vacio, toast, falla, debounce, visor, confirmar, menu, ESTADOS,
} from "../core.js";
import { contadores } from "../app.js";
import { nuevaCotizacion, selectorCliente, tablaPartidas } from "./acciones.js";

const FILTROS = [["abiertas", "Abiertas"], ["", "Todas"], ["borrador", "Borrador"], ["enviada", "Enviadas"],
  ["aprobada", "Aprobadas"], ["rechazada", "Rechazadas"], ["vencida", "Vencidas"]];

// ================================================================ lista

export async function lista(el) {
  const qs = new URLSearchParams(location.hash.split("?")[1] || "");
  let estado = qs.get("estado") ?? "abiertas";
  let q = "";

  el.innerHTML = `
    <div class="page">
      <div class="head">
        <div class="grow"><h1>Cotizaciones</h1><p>Todas las cotizaciones por folio, cliente y estado.</p></div>
        <button class="btn primario" id="nueva">${icono("mas")}Nueva cotización</button>
      </div>
      <div class="barra">
        <div class="segmento" role="group" aria-label="Filtrar por estado">
          ${FILTROS.map(([v, t]) => `<button type="button" data-e="${v}" aria-pressed="${v === estado}">${t}</button>`).join("")}
        </div>
        <input class="input buscar" type="search" placeholder="Buscar folio, cliente o proyecto" aria-label="Buscar">
      </div>
      <section class="card"><div id="tabla"></div></section>
    </div>`;

  const cargar = async () => {
    const rows = await api(`/cotizaciones?estado=${estado}&q=${encodeURIComponent(q)}`);
    el.querySelector("#tabla").innerHTML = rows.length ? `
      <div class="scroll-x"><table class="tabla">
        <thead><tr><th>Folio</th><th>Cliente</th><th>Proyecto</th><th>Fecha</th><th>Estado</th><th class="der">Partidas</th><th class="der">Total</th></tr></thead>
        <tbody>${rows.map((c) => `
          <tr class="click" data-id="${c.id}">
            <td class="folio">${esc(c.folio)}</td>
            <td style="font-weight:600;color:var(--ink)">${esc(c.cliente)}</td>
            <td class="muted">${esc(c.titulo || "")}</td>
            <td class="muted num">${fecha(c.fecha, true)}</td>
            <td>${pill(c.estado)}</td>
            <td class="der num muted">${c.partidas}</td>
            <td class="der num" style="font-weight:600;color:var(--ink)">${dinero(c.total)}</td>
          </tr>`).join("")}</tbody>
      </table></div>`
      : vacio(q ? "Sin resultados" : "No hay cotizaciones aquí", q ? "Prueba con otro folio o nombre de cliente." : "Crea una cotización y aparecerá en esta lista.");
  };

  el.querySelector("#nueva").onclick = () => nuevaCotizacion();
  el.querySelector(".segmento").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    estado = b.dataset.e;
    el.querySelectorAll(".segmento button").forEach((x) => x.setAttribute("aria-pressed", x === b));
    cargar();
  });
  el.querySelector(".buscar").addEventListener("input", debounce((e) => { q = e.target.value.trim(); cargar(); }, 200));
  el.querySelector("#tabla").addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-id]");
    if (tr) location.hash = `#/cotizacion/${tr.dataset.id}`;
  });
  await cargar();
}

// ================================================================ editor

function calcular(items, ivaPct) {
  const bruto = items.reduce((s, i) => s + i.cantidad * i.precio_unitario, 0);
  const desc = items.reduce((s, i) => s + i.cantidad * i.precio_unitario * (i.descuento_pct || 0) / 100, 0);
  const base = bruto - desc;
  const iva = Math.round(base * ivaPct) / 100;
  return { subtotal: bruto, descuento: desc, iva, total: base + iva };
}

export async function editor(el, id) {
  let cot = await api(`/cotizaciones/${id}`);
  const items = cot.items.map((i) => ({ ...i }));

  el.innerHTML = `
    <div class="page">
      <div class="editor-top">
        <a class="migas" href="#/cotizaciones">${icono("atras")}Cotizaciones</a>
        <span class="doc-folio">${esc(cot.folio)}</span>
        <select class="estado" id="estado" aria-label="Estado">${Object.entries(ESTADOS).slice(0, 5).map(([v, t]) => `<option value="${v}">${t}</option>`).join("")}</select>
        <span class="grow"></span>
        <span class="guardado" id="guardado" aria-live="polite">Guardado</span>
        <button class="btn" id="previa">${icono("ojo")}Vista previa</button>
        <button class="btn primario" id="exportar">${icono("pdf")}Exportar PDF</button>
        <div class="menu">
          <button class="btn icono" id="mas" aria-label="Más acciones">${icono("mas-h")}</button>
          <div class="menu-lista" hidden>
            <button type="button" data-a="nota">${icono("nota")}Crear nota de entrega</button>
            <button type="button" data-a="duplicar">${icono("cot")}Duplicar cotización</button>
            <hr>
            <button type="button" class="peligro" data-a="eliminar">${icono("x")}Eliminar</button>
          </div>
        </div>
      </div>

      <div class="editor">
        <div class="col">
          <section class="card">
            <header><h2>Datos generales</h2></header>
            <div class="cuerpo rejilla" style="grid-template-columns:repeat(auto-fill,minmax(160px,1fr))">
              <label class="campo ancho">Cliente<div id="cliente"></div></label>
              <label class="campo ancho">Proyecto o referencia<input class="input" data-c="titulo" value="${esc(cot.titulo)}" placeholder="Ej. Sistema CCTV bodega norte"></label>
              <label class="campo">Fecha<input class="input" type="date" data-c="fecha" value="${cot.fecha}"></label>
              <label class="campo">Vigencia (días)<input class="input" type="number" min="1" data-c="vigencia_dias" value="${cot.vigencia_dias}"></label>
              <label class="campo">Vence<input class="input" id="vence" disabled value="${fecha(cot.vence, true)}"></label>
            </div>
          </section>

          <section class="card">
            <header><h2>Partidas</h2><span class="muted small" id="n-partidas"></span></header>
            <div id="partidas"></div>
          </section>

          <section class="card">
            <header><h2>Condiciones</h2></header>
            <div class="cuerpo rejilla">
              <label class="campo">Tiempo de entrega<input class="input" data-c="tiempo_entrega" value="${esc(cot.tiempo_entrega)}"></label>
              <label class="campo">Forma de pago<input class="input" data-c="forma_pago" value="${esc(cot.forma_pago)}"></label>
              <label class="campo ancho">Condiciones comerciales (salen en el PDF)<textarea class="input" data-c="condiciones" rows="3">${esc(cot.condiciones)}</textarea></label>
              <label class="campo ancho">Notas internas (no salen en el PDF)<textarea class="input" data-c="notas_internas" rows="2">${esc(cot.notas_internas)}</textarea></label>
            </div>
          </section>
        </div>

        <aside>
          <section class="card">
            <div class="totales"><dl>
              <dt>Subtotal</dt><dd id="t-sub"></dd>
              <dt>Descuento</dt><dd id="t-desc"></dd>
              <dt class="iva">IVA <input class="input" data-c="iva_pct" inputmode="decimal" value="${cot.iva_pct}" aria-label="Porcentaje de IVA">%</dt><dd id="t-iva"></dd>
              <dt class="total">Total</dt><dd class="total" id="t-total"></dd>
            </dl></div>
            <div class="margen" title="Calculado con el costo registrado en inventario. Solo se ve aquí."><span>Margen estimado</span><b id="t-margen"></b></div>
          </section>
          <section class="card" id="relacionados"></section>
        </aside>
      </div>
    </div>`;

  const $ = (s) => el.querySelector(s);
  const selEstado = $("#estado");
  const pintarEstado = () => {
    selEstado.value = cot.estado;
    selEstado.className = `estado e-${cot.estado}`;
  };
  pintarEstado();

  const relacionados = () => {
    const docs = cot.documentos.map((d) => `
      <li><a href="/api/documentos/${d.id}/archivo" target="_blank" rel="noopener">${icono("archivo")}<span>${esc(d.archivo.split("/").pop())}</span><small>${fecha(d.creado)}</small></a></li>`).join("");
    const notas = cot.notas.map((n) => `
      <li><a href="#/nota/${n.id}">${icono("nota")}<span>${esc(n.folio)}</span>${pill(n.estado)}</a></li>`).join("");
    $("#relacionados").innerHTML = `
      <header><h2>PDF exportados</h2></header>
      ${docs ? `<ul class="docs-lista">${docs}</ul>` : `<p class="muted small" style="padding:0 18px 14px;margin:0">Aún no se exporta. Al exportar se guarda en la carpeta del cliente.</p>`}
      ${notas ? `<header style="padding-top:4px"><h2>Notas de entrega</h2></header><ul class="docs-lista">${notas}</ul>` : ""}`;
  };
  relacionados();

  let inv;
  const totales = () => {
    const t = calcular(items, parseFloat($('[data-c="iva_pct"]').value) || 0);
    $("#t-sub").textContent = dinero(t.subtotal);
    $("#t-desc").textContent = t.descuento ? `−${dinero(t.descuento)}` : dinero(0);
    $("#t-iva").textContent = dinero(t.iva);
    $("#t-total").textContent = dinero(t.total);
    $("#n-partidas").textContent = items.length ? `${items.length} ${items.length === 1 ? "partida" : "partidas"}` : "";
    const venta = t.subtotal - t.descuento;
    const mapa = inv?.inventario() || {};
    const conCosto = items.filter((i) => mapa[i.inventario_id]?.costo);
    if (!venta || !conCosto.length) { $("#t-margen").textContent = "—"; return; }
    const costo = conCosto.reduce((s, i) => s + mapa[i.inventario_id].costo * i.cantidad, 0);
    const ventaConCosto = conCosto.reduce((s, i) => s + i.cantidad * i.precio_unitario * (1 - (i.descuento_pct || 0) / 100), 0);
    $("#t-margen").textContent = `${Math.round(((ventaConCosto - costo) / ventaConCosto) * 100)}%`;
  };

  // ---------- guardado automático
  let cliente_id = cot.cliente_id;
  let version = 0;
  let guardada = 0;
  const indicador = $("#guardado");
  const guardar = debounce(async () => {
    const v = version;
    const cuerpo = { cliente_id, items };
    el.querySelectorAll("[data-c]").forEach((i) => { cuerpo[i.dataset.c] = i.value; });
    indicador.textContent = "Guardando…";
    indicador.className = "guardado activo";
    try {
      const r = await api(`/cotizaciones/${id}`, { method: "PUT", body: cuerpo });
      cot = { ...r, documentos: cot.documentos };
      guardada = v;
      if (version === v) {
        indicador.textContent = "Guardado";
        indicador.className = "guardado";
      }
      $("#vence").value = fecha(r.vence, true);
      pintarEstado();
    } catch (e) {
      indicador.textContent = "Sin guardar";
      indicador.className = "guardado error";
      falla(e);
    }
  }, 600);
  const cambio = () => {
    version++;
    indicador.textContent = "Editando…";
    indicador.className = "guardado activo";
    totales();
    guardar();
  };
  const asegurar = async () => { if (guardada !== version) await guardar.ahora(); };

  selectorCliente($("#cliente"), cot.cliente, (c) => { cliente_id = c?.id || null; cambio(); });
  el.querySelectorAll("[data-c]").forEach((i) => i.addEventListener("input", cambio));
  inv = await tablaPartidas($("#partidas"), items, { conPrecio: true, alCambiar: cambio });
  totales();

  selEstado.addEventListener("change", async () => {
    try {
      await asegurar();
      cot = { ...(await api(`/cotizaciones/${id}/estado`, { method: "POST", body: { estado: selEstado.value } })) };
      pintarEstado();
      relacionados();
      contadores();
      toast(`Marcada como ${ESTADOS[cot.estado].toLowerCase()}`);
    } catch (e) { falla(e); pintarEstado(); }
  });

  const exportar = async () => {
    await asegurar();
    try {
      const r = await api(`/cotizaciones/${id}/exportar`, { method: "POST" });
      toast(`PDF guardado en ${esc(r.archivo)} · <a href="${r.url}" target="_blank" rel="noopener">Abrir</a>`, { html: true, ms: 6000 });
      cot = await api(`/cotizaciones/${id}`);
      pintarEstado();
      relacionados();
      contadores();
      return true;
    } catch (e) { falla(e); return false; }
  };

  $("#exportar").onclick = exportar;
  $("#previa").onclick = async () => {
    await asegurar();
    const d = visor(`Vista previa · ${cot.folio}`, `/api/cotizaciones/${id}/vista.pdf`,
      `<button type="button" class="btn primario" data-exp>${icono("pdf")}Exportar PDF</button>`);
    d.querySelector("[data-exp]").onclick = async () => { if (await exportar()) d.close(); };
  };

  menu($("#mas"), el.querySelector(".menu-lista"));
  el.querySelector(".menu-lista").addEventListener("click", async (e) => {
    const a = e.target.closest("button")?.dataset.a;
    if (!a) return;
    await asegurar();
    try {
      if (a === "duplicar") {
        const d = await api(`/cotizaciones/${id}/duplicar`, { method: "POST" });
        toast(`Duplicada como ${d.folio}`);
        location.hash = `#/cotizacion/${d.id}`;
      } else if (a === "nota") {
        const n = await api(`/cotizaciones/${id}/nota`, { method: "POST" });
        toast(`Nota ${n.folio} creada con las partidas de esta cotización`);
        location.hash = `#/nota/${n.id}`;
      } else if (a === "eliminar" && await confirmar("Eliminar cotización", `Se quitará <b>${esc(cot.folio)}</b> de las listas. Los PDF ya exportados se conservan en su carpeta.`, "Eliminar")) {
        await api(`/cotizaciones/${id}`, { method: "DELETE" });
        toast(`${cot.folio} eliminada`);
        location.hash = "#/cotizaciones";
      }
    } catch (err) { falla(err); }
  });

  // Al salir de la pantalla se guarda lo que esté pendiente.
  return asegurar;
}
