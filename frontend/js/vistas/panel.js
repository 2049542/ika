import { api, esc, dinero, dineroCorto, fecha, hace, pill, icono, vacio, num } from "../core.js";
import { nuevaCotizacion, nuevaNota } from "./acciones.js";

function saludo() {
  const h = new Date().getHours();
  return h < 12 ? "Buenos días" : h < 19 ? "Buenas tardes" : "Buenas noches";
}

export async function render(el) {
  const p = await api("/panel");
  const hoy = new Date().toLocaleDateString("es-MX", { weekday: "long", day: "numeric", month: "long" });
  const max = Math.max(1, ...p.por_cliente.map((g) => g.monto));

  const grupos = p.por_cliente.map((g) => `
    <details class="grupo">
      <summary>
        <div class="nombre">${esc(g.cliente)}<small>${g.cotizaciones.length} ${g.cotizaciones.length === 1 ? "abierta" : "abiertas"} · la más antigua ${hace(g.mas_antigua)}</small></div>
        <div class="barra-monto"><i style="--w:${(g.monto / max) * 100}%"></i></div>
        <div class="monto">${dineroCorto(g.monto)}</div>
        <svg class="chev"><use href="#i-chev"/></svg>
      </summary>
      <div class="filas">
        ${g.cotizaciones.map((c) => `
          <a href="#/cotizacion/${c.id}">
            <span class="folio" style="font:600 13.5px var(--display);color:var(--ink)">${esc(c.folio)}</span>
            <span class="titulo">${esc(c.titulo || "Sin título")} · ${fecha(c.fecha)}</span>
            ${pill(c.estado)}
            <span class="num" style="text-align:right;font-weight:600;color:var(--ink)">${dinero(c.total)}</span>
          </a>`).join("")}
      </div>
    </details>`).join("");

  el.innerHTML = `
    <div class="page entra">
      <div class="head" style="--i:0">
        <div class="grow"><h1>${saludo()}</h1><p>${hoy.charAt(0).toUpperCase() + hoy.slice(1)}</p></div>
        <div class="acciones">
          <button class="btn" id="nueva-nota">${icono("nota")}Nota de entrega</button>
          <button class="btn primario" id="nueva-cot">${icono("mas")}Nueva cotización</button>
        </div>
      </div>

      <div class="kpis" style="--i:1">
        <a class="kpi" href="#/cotizaciones?estado=abiertas"><span>Cotizaciones abiertas</span><b>${dineroCorto(p.abiertas.monto)}</b><small>${p.abiertas.n} entre borradores y enviadas</small></a>
        <div class="kpi ${p.por_vencer.length ? "alerta" : ""}"><span>Por vencer en 5 días</span><b>${p.por_vencer.length}</b><small>${p.por_vencer.length ? dineroCorto(p.por_vencer.reduce((s, c) => s + c.total, 0)) + " en juego" : "Nada urgente"}</small></div>
        <div class="kpi"><span>Aprobadas este mes</span><b>${dineroCorto(p.aprobadas_mes.monto)}</b><small>${p.aprobadas_mes.n} ${p.aprobadas_mes.n === 1 ? "cotización" : "cotizaciones"}</small></div>
        <a class="kpi" href="#/notas"><span>Notas por entregar</span><b>${p.notas_pendientes.length}</b><small>${p.stock_bajo.length ? `${p.stock_bajo.length} artículos con stock bajo` : "Inventario en orden"}</small></a>
      </div>

      <div class="panel-grid" style="--i:2">
        <section class="card">
          <header><h2>Abiertas por cliente</h2><a class="btn fantasma chico" href="#/cotizaciones">Ver todas</a></header>
          ${grupos || vacio("No hay cotizaciones abiertas", "Las cotizaciones en borrador o enviadas aparecen aquí agrupadas por cliente.")}
        </section>

        <div class="panel-lado">
          <section class="card">
            <header><h2>Por vencer</h2></header>
            ${p.por_vencer.length ? `<ul class="lista-mini">${p.por_vencer.map((c) => `
              <li><a href="#/cotizacion/${c.id}"><div class="t"><b>${esc(c.folio)} · ${esc(c.cliente || "Sin cliente")}</b><span>Vence ${fecha(c.vence)}</span></div><span class="v alerta">${dineroCorto(c.total)}</span></a></li>`).join("")}</ul>`
              : `<p class="muted small" style="padding:0 18px 16px;margin:0">Ninguna cotización enviada vence en los próximos 5 días.</p>`}
          </section>

          <section class="card">
            <header><h2>Notas por entregar</h2></header>
            ${p.notas_pendientes.length ? `<ul class="lista-mini">${p.notas_pendientes.map((n) => `
              <li><a href="#/nota/${n.id}"><div class="t"><b>${esc(n.folio)} · ${esc(n.cliente)}</b><span>${n.partidas} partidas · ${fecha(n.fecha)}</span></div></a></li>`).join("")}</ul>`
              : `<p class="muted small" style="padding:0 18px 16px;margin:0">Todo entregado.</p>`}
          </section>

          ${p.stock_bajo.length ? `<section class="card">
            <header><h2>Stock bajo</h2><a class="btn fantasma chico" href="#/inventario">Inventario</a></header>
            <ul class="lista-mini">${p.stock_bajo.map((i) => `
              <li><a href="#/inventario"><div class="t"><b>${esc(i.nombre)}</b><span>Mínimo ${num(i.stock_minimo)} ${esc(i.unidad)}</span></div><span class="v alerta">${num(i.stock)}</span></a></li>`).join("")}</ul>
          </section>` : ""}
        </div>
      </div>
    </div>`;

  el.querySelector("#nueva-cot").onclick = () => nuevaCotizacion();
  el.querySelector("#nueva-nota").onclick = () => nuevaNota();
  el.querySelectorAll(".entra > *").forEach((n, i) => n.style.setProperty("--i", i));
}
