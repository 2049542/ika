import { api, esc, fecha, icono, vacio, falla, debounce } from "../core.js";

export async function render(el) {
  let q = "";
  el.innerHTML = `
    <div class="page">
      <div class="head">
        <div class="grow"><h1>Documentos</h1><p>Cada PDF exportado, guardado en <b>documentos/Cliente/</b> con el nombre del cliente y el folio.</p></div>
        <button class="btn" id="carpeta">${icono("docs")}Abrir carpeta</button>
      </div>
      <div class="barra"><input class="input buscar" type="search" placeholder="Buscar cliente o folio" aria-label="Buscar"></div>
      <div id="grupos" style="display:grid;gap:18px"></div>
    </div>`;

  const cargar = async () => {
    const docs = await api(`/documentos?q=${encodeURIComponent(q)}`);
    const grupos = {};
    docs.forEach((d) => { (grupos[d.cliente] ||= { id: d.cliente_id, docs: [] }).docs.push(d); });
    el.querySelector("#grupos").innerHTML = docs.length ? Object.entries(grupos).map(([cliente, g]) => `
      <section class="card">
        <header><h2>${esc(cliente)}</h2><span class="muted small">${g.docs.length} PDF</span>
          ${g.id ? `<button class="btn fantasma chico" data-carpeta="${g.id}">${icono("docs")}Carpeta</button><a class="btn fantasma chico" href="#/cliente/${g.id}">Ver cliente</a>` : ""}</header>
        <div class="scroll-x"><table class="tabla"><tbody>${g.docs.map((d) => `
          <tr>
            <td style="width:150px">${d.tipo === "cotizacion" ? "Cotización" : "Nota de entrega"}</td>
            <td class="folio" style="width:140px">${esc(d.folio)}</td>
            <td>${d.existe ? `<a href="/api/documentos/${d.id}/archivo" target="_blank" rel="noopener">${esc(d.archivo.split("/").pop())}</a>` : `<span class="faint">${esc(d.archivo.split("/").pop())} (se movió o borró de la carpeta)</span>`}</td>
            <td class="der muted num" style="width:120px">${fecha(d.creado, true)}</td>
          </tr>`).join("")}</tbody></table></div>
      </section>`).join("")
      : `<section class="card">${vacio(q ? "Sin resultados" : "Todavía no hay PDF exportados", q ? "Prueba con otro cliente o folio." : "Usa “Exportar PDF” en una cotización o nota de entrega.")}</section>`;
  };

  const abrir = (cliente_id) => api("/documentos/abrir-carpeta", { method: "POST", body: { cliente_id } }).catch(falla);
  el.querySelector("#carpeta").onclick = () => abrir(null);
  el.querySelector("#grupos").addEventListener("click", (e) => {
    const b = e.target.closest("[data-carpeta]");
    if (b) abrir(+b.dataset.carpeta);
  });
  el.querySelector(".buscar").addEventListener("input", debounce((e) => { q = e.target.value.trim(); cargar(); }, 200));
  await cargar();
}
