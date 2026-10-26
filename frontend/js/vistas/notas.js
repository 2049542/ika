import { api, esc, fecha, pill, icono, vacio, toast, falla, debounce, visor, confirmar, menu } from "../core.js";
import { contadores } from "../app.js";
import { nuevaNota, selectorCliente, tablaPartidas } from "./acciones.js";

// ================================================================ lista

export async function lista(el) {
  let estado = "";
  let q = "";
  el.innerHTML = `
    <div class="page">
      <div class="head">
        <div class="grow"><h1>Notas de entrega</h1><p>Lo que sale a cada cliente. Al marcarla como entregada se descuenta del inventario.</p></div>
        <button class="btn primario" id="nueva">${icono("mas")}Nueva nota</button>
      </div>
      <div class="barra">
        <div class="segmento" role="group" aria-label="Filtrar por estado">
          <button type="button" data-e="" aria-pressed="true">Todas</button>
          <button type="button" data-e="pendiente" aria-pressed="false">Por entregar</button>
          <button type="button" data-e="entregada" aria-pressed="false">Entregadas</button>
        </div>
        <input class="input buscar" type="search" placeholder="Buscar folio, cliente o cotización" aria-label="Buscar">
      </div>
      <section class="card"><div id="tabla"></div></section>
    </div>`;

  const cargar = async () => {
    const rows = await api(`/notas?estado=${estado}&q=${encodeURIComponent(q)}`);
    el.querySelector("#tabla").innerHTML = rows.length ? `
      <div class="scroll-x"><table class="tabla">
        <thead><tr><th>Folio</th><th>Cliente</th><th>Cotización</th><th>Fecha</th><th>Estado</th><th class="der">Partidas</th></tr></thead>
        <tbody>${rows.map((n) => `
          <tr class="click" data-id="${n.id}">
            <td class="folio">${esc(n.folio)}</td>
            <td style="font-weight:600;color:var(--ink)">${esc(n.cliente)}</td>
            <td class="muted">${esc(n.cotizacion_folio || "")}</td>
            <td class="muted num">${fecha(n.fecha, true)}</td>
            <td>${pill(n.estado)}</td>
            <td class="der num muted">${n.partidas}</td>
          </tr>`).join("")}</tbody>
      </table></div>`
      : vacio(q ? "Sin resultados" : "No hay notas de entrega", q ? "Prueba con otro folio o cliente." : "Crea una desde cero o desde una cotización aprobada (menú ⋯ de la cotización).");
  };

  el.querySelector("#nueva").onclick = () => nuevaNota();
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
    if (tr) location.hash = `#/nota/${tr.dataset.id}`;
  });
  await cargar();
}

// ================================================================ editor

export async function editor(el, id) {
  let nota = await api(`/notas/${id}`);
  const items = nota.items.map((i) => ({ ...i }));
  const entregada = nota.estado === "entregada";

  el.innerHTML = `
    <div class="page">
      <div class="editor-top">
        <a class="migas" href="#/notas">${icono("atras")}Notas</a>
        <span class="doc-folio">${esc(nota.folio)}</span>
        ${pill(nota.estado)}
        <span class="grow"></span>
        <span class="guardado" id="guardado" aria-live="polite">Guardado</span>
        <button class="btn" id="estado">${entregada ? "Regresar a pendiente" : "Marcar como entregada"}</button>
        <button class="btn" id="previa">${icono("ojo")}Vista previa</button>
        <button class="btn primario" id="exportar">${icono("pdf")}Exportar PDF</button>
        <div class="menu">
          <button class="btn icono" id="mas" aria-label="Más acciones">${icono("mas-h")}</button>
          <div class="menu-lista" hidden><button type="button" class="peligro" data-a="eliminar">${icono("x")}Eliminar</button></div>
        </div>
      </div>

      <div class="editor">
        <div class="col">
          <section class="card">
            <header><h2>Entrega</h2>${nota.cotizacion_id ? `<a class="btn fantasma chico" href="#/cotizacion/${nota.cotizacion_id}">De la cotización ${esc(nota.cotizacion_folio)}</a>` : ""}</header>
            <div class="cuerpo rejilla">
              <label class="campo ancho">Cliente<div id="cliente"></div></label>
              <label class="campo">Fecha<input class="input" type="date" data-c="fecha" value="${nota.fecha}"></label>
              <label class="campo">Recibe<input class="input" data-c="recibe" value="${esc(nota.recibe)}" placeholder="Nombre de quien recibe"></label>
              <label class="campo ancho">Dirección de entrega<input class="input" data-c="direccion_entrega" value="${esc(nota.direccion_entrega)}"></label>
            </div>
          </section>

          <section class="card">
            <header><h2>Material y servicios entregados</h2><span class="muted small">${entregada ? "Entregada: regrésala a pendiente para editar" : ""}</span></header>
            <div id="partidas"></div>
          </section>

          <section class="card">
            <header><h2>Observaciones</h2></header>
            <div class="cuerpo"><textarea class="input" data-c="observaciones" rows="3" placeholder="Salen en el PDF, arriba de las firmas">${esc(nota.observaciones)}</textarea></div>
          </section>
        </div>

        <aside>
          <section class="card" id="relacionados"></section>
        </aside>
      </div>
    </div>`;

  const $ = (s) => el.querySelector(s);
  const relacionados = () => {
    const docs = nota.documentos.map((d) => `
      <li><a href="/api/documentos/${d.id}/archivo" target="_blank" rel="noopener">${icono("archivo")}<span>${esc(d.archivo.split("/").pop())}</span><small>${fecha(d.creado)}</small></a></li>`).join("");
    const piezas = items.reduce((s, i) => s + (+i.cantidad || 0), 0);
    $("#relacionados").innerHTML = `
      <div class="totales"><dl>
        <dt>Partidas</dt><dd>${items.length}</dd>
        <dt class="total">Unidades</dt><dd class="total">${piezas.toLocaleString("es-MX")}</dd>
      </dl></div>
      <header style="border-top:1px solid var(--line)"><h2>PDF exportados</h2></header>
      ${docs ? `<ul class="docs-lista">${docs}</ul>` : `<p class="muted small" style="padding:0 18px 14px;margin:0">Aún no se exporta.</p>`}`;
  };
  relacionados();

  let cliente_id = nota.cliente_id;
  let version = 0;
  let guardada = 0;
  const indicador = $("#guardado");
  const guardar = debounce(async () => {
    const v = version;
    const cuerpo = { cliente_id };
    if (!entregada) cuerpo.items = items;
    el.querySelectorAll("[data-c]").forEach((i) => { cuerpo[i.dataset.c] = i.value; });
    indicador.textContent = "Guardando…";
    try {
      nota = await api(`/notas/${id}`, { method: "PUT", body: cuerpo });
      guardada = v;
      if (version === v) indicador.textContent = "Guardado";
      indicador.className = "guardado";
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
    relacionados();
    guardar();
  };
  const asegurar = async () => { if (guardada !== version) await guardar.ahora(); };

  selectorCliente($("#cliente"), nota.cliente, (c) => {
    cliente_id = c?.id || null;
    const dir = $('[data-c="direccion_entrega"]');
    if (c?.direccion && !dir.value) dir.value = c.direccion;
    cambio();
  });
  el.querySelectorAll("[data-c]").forEach((i) => i.addEventListener("input", cambio));
  await tablaPartidas($("#partidas"), items, { conPrecio: false, alCambiar: cambio, bloqueado: entregada });

  $("#estado").onclick = async () => {
    await asegurar();
    const nuevo = entregada ? "pendiente" : "entregada";
    const ok = await confirmar(
      entregada ? "Regresar a pendiente" : "Marcar como entregada",
      entregada ? "Las existencias que se descontaron vuelven al inventario." : "Se descontarán del inventario los productos de esta nota. Los servicios y el personal no llevan existencias.",
      entregada ? "Regresar" : "Marcar entregada");
    if (!ok) return;
    try {
      await api(`/notas/${id}/estado`, { method: "POST", body: { estado: nuevo } });
      toast(entregada ? "Nota regresada a pendiente" : "Nota entregada; inventario actualizado");
      contadores();
      editor(el, id);
    } catch (e) { falla(e); }
  };

  const exportar = async () => {
    await asegurar();
    try {
      const r = await api(`/notas/${id}/exportar`, { method: "POST" });
      toast(`PDF guardado en ${esc(r.archivo)} · <a href="${r.url}" target="_blank" rel="noopener">Abrir</a>`, { html: true, ms: 6000 });
      nota = await api(`/notas/${id}`);
      relacionados();
      return true;
    } catch (e) { falla(e); return false; }
  };
  $("#exportar").onclick = exportar;
  $("#previa").onclick = async () => {
    await asegurar();
    const d = visor(`Vista previa · ${nota.folio}`, `/api/notas/${id}/vista.pdf`,
      `<button type="button" class="btn primario" data-exp>${icono("pdf")}Exportar PDF</button>`);
    d.querySelector("[data-exp]").onclick = async () => { if (await exportar()) d.close(); };
  };

  menu($("#mas"), el.querySelector(".menu-lista"));
  el.querySelector(".menu-lista").addEventListener("click", async (e) => {
    if (e.target.closest("button")?.dataset.a !== "eliminar") return;
    if (!await confirmar("Eliminar nota", `Se quitará <b>${esc(nota.folio)}</b> de las listas.`, "Eliminar")) return;
    try {
      await api(`/notas/${id}`, { method: "DELETE" });
      toast(`${nota.folio} eliminada`);
      contadores();
      location.hash = "#/notas";
    } catch (err) { falla(err); }
  });

  return asegurar;
}
