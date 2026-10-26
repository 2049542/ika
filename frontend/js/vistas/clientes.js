import { api, esc, dinero, dineroCorto, fecha, pill, icono, vacio, toast, falla, debounce, dialogo, datosForm, confirmar } from "../core.js";
import { camposCliente, clienteRapido, nuevaCotizacion, nuevaNota } from "./acciones.js";

export async function lista(el) {
  let q = "";
  el.innerHTML = `
    <div class="page">
      <div class="head">
        <div class="grow"><h1>Clientes</h1><p>Lo abierto, lo aprobado y todos los documentos de cada cliente.</p></div>
        <button class="btn primario" id="nuevo">${icono("mas")}Nuevo cliente</button>
      </div>
      <div class="barra"><input class="input buscar" type="search" placeholder="Buscar por nombre, RFC o contacto" aria-label="Buscar"></div>
      <section class="card"><div id="tabla"></div></section>
    </div>`;

  const cargar = async () => {
    const rows = await api(`/clientes?q=${encodeURIComponent(q)}`);
    el.querySelector("#tabla").innerHTML = rows.length ? `
      <div class="scroll-x"><table class="tabla">
        <thead><tr><th>Cliente</th><th>Contacto</th><th class="der">Abiertas</th><th class="der">Monto abierto</th><th class="der">Aprobado</th><th>Última cotización</th></tr></thead>
        <tbody>${rows.map((c) => `
          <tr class="click" data-id="${c.id}">
            <td style="font-weight:600;color:var(--ink)">${esc(c.nombre)}${c.rfc ? `<div class="faint small">${esc(c.rfc)}</div>` : ""}</td>
            <td class="muted">${esc(c.contacto || "")}</td>
            <td class="der num">${c.abiertas || "—"}</td>
            <td class="der num" style="font-weight:600;color:var(--ink)">${c.monto_abierto ? dineroCorto(c.monto_abierto) : "—"}</td>
            <td class="der num muted">${c.monto_aprobado ? dineroCorto(c.monto_aprobado) : "—"}</td>
            <td class="muted num">${c.ultima ? fecha(c.ultima, true) : "Sin cotizaciones"}</td>
          </tr>`).join("")}</tbody>
      </table></div>`
      : vacio(q ? "Sin resultados" : "Aún no hay clientes", q ? "Prueba con otro nombre." : "Da de alta un cliente aquí o directo desde una cotización.");
  };

  el.querySelector("#nuevo").onclick = async () => {
    const c = await clienteRapido();
    if (c) location.hash = `#/cliente/${c.id}`;
  };
  el.querySelector(".buscar").addEventListener("input", debounce((e) => { q = e.target.value.trim(); cargar(); }, 200));
  el.querySelector("#tabla").addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-id]");
    if (tr) location.hash = `#/cliente/${tr.dataset.id}`;
  });
  await cargar();
}

export async function detalle(el, id) {
  const c = await api(`/clientes/${id}`);
  const abiertas = c.cotizaciones.filter((x) => ["borrador", "enviada"].includes(x.estado));
  const aprobado = c.cotizaciones.filter((x) => x.estado === "aprobada").reduce((s, x) => s + x.total, 0);
  const datos = [c.contacto, c.rfc && `RFC ${c.rfc}`, c.telefono, c.email, c.direccion].filter(Boolean);

  el.innerHTML = `
    <div class="page entra">
      <div class="head">
        <div class="grow">
          <a class="btn fantasma chico" href="#/clientes" style="margin-left:-10px;margin-bottom:6px">${icono("atras")}Clientes</a>
          <h1>${esc(c.nombre)}</h1>
          <p>${datos.map(esc).join("  ·  ") || "Sin datos de contacto"}</p>
        </div>
        <div class="acciones">
          <button class="btn fantasma" id="editar">Editar datos</button>
          <button class="btn" id="carpeta">${icono("docs")}Abrir carpeta</button>
          <button class="btn" id="nota">${icono("nota")}Nota de entrega</button>
          <button class="btn primario" id="cot">${icono("mas")}Cotizar</button>
        </div>
      </div>

      <div class="kpis" style="grid-template-columns:repeat(3,1fr)">
        <div class="kpi"><span>Abierto</span><b>${dineroCorto(abiertas.reduce((s, x) => s + x.total, 0))}</b><small>${abiertas.length} cotizaciones</small></div>
        <div class="kpi"><span>Aprobado histórico</span><b>${dineroCorto(aprobado)}</b><small>${c.cotizaciones.filter((x) => x.estado === "aprobada").length} cotizaciones</small></div>
        <div class="kpi"><span>Documentos exportados</span><b>${c.documentos.length}</b><small>${c.notas.length} notas de entrega</small></div>
      </div>

      <div class="panel-grid">
        <section class="card">
          <header><h2>Cotizaciones</h2></header>
          ${c.cotizaciones.length ? `<div class="scroll-x"><table class="tabla"><tbody>${c.cotizaciones.map((x) => `
            <tr class="click" data-href="#/cotizacion/${x.id}">
              <td class="folio">${esc(x.folio)}</td><td class="muted">${esc(x.titulo || "")}</td>
              <td class="muted num">${fecha(x.fecha, true)}</td><td>${pill(x.estado)}</td>
              <td class="der num" style="font-weight:600;color:var(--ink)">${dinero(x.total)}</td>
            </tr>`).join("")}</tbody></table></div>` : vacio("Sin cotizaciones", "Usa “Cotizar” para crear la primera.")}
        </section>
        <div class="panel-lado">
          <section class="card">
            <header><h2>Notas de entrega</h2></header>
            ${c.notas.length ? `<ul class="lista-mini">${c.notas.map((n) => `
              <li><a href="#/nota/${n.id}"><div class="t"><b>${esc(n.folio)}</b><span>${fecha(n.fecha, true)}</span></div>${pill(n.estado)}</a></li>`).join("")}</ul>`
              : `<p class="muted small" style="padding:0 18px 16px;margin:0">Sin notas.</p>`}
          </section>
          <section class="card">
            <header><h2>Archivo PDF</h2></header>
            ${c.documentos.length ? `<ul class="docs-lista">${c.documentos.map((d) => `
              <li><a href="/api/documentos/${d.id}/archivo" target="_blank" rel="noopener">${icono("archivo")}<span>${esc(d.archivo.split("/").pop())}</span><small>${fecha(d.creado)}</small></a></li>`).join("")}</ul>`
              : `<p class="muted small" style="padding:0 18px 16px;margin:0">Lo que exportes se guarda en documentos/${esc(c.nombre)}/</p>`}
          </section>
        </div>
      </div>
    </div>`;

  el.querySelectorAll(".entra > *").forEach((n, i) => n.style.setProperty("--i", i));
  el.querySelector("#cot").onclick = () => nuevaCotizacion(c.id);
  el.querySelector("#nota").onclick = () => nuevaNota(c.id);
  el.querySelector("#carpeta").onclick = () => api("/documentos/abrir-carpeta", { method: "POST", body: { cliente_id: c.id } }).catch(falla);
  el.querySelector("tbody")?.addEventListener("click", (e) => {
    const tr = e.target.closest("tr[data-href]");
    if (tr) location.hash = tr.dataset.href;
  });
  el.querySelector("#editar").onclick = () => {
    const d = dialogo({
      titulo: "Datos del cliente", cuerpo: camposCliente(c) + `
        <label class="campo" style="margin-top:14px">Notas<textarea class="input" name="notas" rows="2">${esc(c.notas)}</textarea></label>`,
      alAceptar: async (form) => {
        await api(`/clientes/${c.id}`, { method: "PUT", body: datosForm(form) });
        toast("Cliente actualizado");
        detalle(el, id);
      },
    });
    if (!c.cotizaciones.length && !c.notas.length) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "btn fantasma peligro";
      b.style.marginRight = "auto";
      b.textContent = "Borrar cliente";
      b.onclick = async () => {
        if (!await confirmar("Borrar cliente", `Se borrará <b>${esc(c.nombre)}</b>.`, "Borrar")) return;
        await api(`/clientes/${c.id}`, { method: "DELETE" }).catch(falla);
        d.close();
        location.hash = "#/clientes";
      };
      d.querySelector("footer").prepend(b);
    }
  };
}
