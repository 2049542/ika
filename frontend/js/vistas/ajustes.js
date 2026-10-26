import { api, esc, toast, falla, datosForm } from "../core.js";

const campo = (a, clave, etiqueta, extra = "") =>
  `<label class="campo ${extra}">${etiqueta}<input class="input" name="${clave}" value="${esc(a[clave])}"></label>`;

export async function render(el) {
  const [a, info] = await Promise.all([api("/ajustes"), api("/ika")]);
  el.innerHTML = `
    <div class="page" style="max-width:860px">
      <div class="head"><div class="grow"><h1>Ajustes</h1><p>Datos que aparecen en los PDF y valores por defecto de cada cotización nueva.</p></div></div>
      <form id="f" style="display:grid;gap:22px">
        <section class="card">
          <header><h2>Logo</h2></header>
          <div class="cuerpo" style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">
            <img class="logo-prev" src="/api/logo?t=${Date.now()}" alt="Logo actual">
            <div style="display:grid;gap:8px">
              <p class="muted small" style="margin:0">Sale arriba a la izquierda en cotizaciones y notas. PNG con fondo transparente o blanco.</p>
              <div class="acciones">
                <label class="btn">Cambiar logo<input type="file" accept="image/*" id="logo" hidden></label>
                ${a.logo_personalizado ? `<button type="button" class="btn fantasma" id="quitar-logo">Volver al logo MR</button>` : ""}
              </div>
            </div>
          </div>
        </section>

        <section class="card">
          <header><h2>Empresa</h2></header>
          <div class="cuerpo rejilla">
            ${campo(a, "empresa_nombre", "Nombre")}
            ${campo(a, "empresa_lema", "Giro o lema")}
            ${campo(a, "empresa_rfc", "RFC")}
            ${campo(a, "empresa_telefono", "Teléfono")}
            ${campo(a, "empresa_email", "Correo")}
            ${campo(a, "empresa_web", "Sitio web")}
            ${campo(a, "empresa_direccion", "Dirección", "ancho")}
            ${campo(a, "firma_nombre", "Firma: nombre")}
            ${campo(a, "firma_puesto", "Firma: puesto")}
          </div>
        </section>

        <section class="card">
          <header><h2>Cotizaciones nuevas</h2></header>
          <div class="cuerpo rejilla">
            ${campo(a, "prefijo_cotizacion", "Prefijo de folio")}
            ${campo(a, "prefijo_nota", "Prefijo de notas")}
            ${campo(a, "iva_pct", "IVA %")}
            ${campo(a, "vigencia_dias", "Vigencia (días)")}
            ${campo(a, "tiempo_entrega", "Tiempo de entrega")}
            ${campo(a, "forma_pago", "Forma de pago")}
            <label class="campo ancho">Condiciones comerciales<textarea class="input" name="condiciones" rows="4">${esc(a.condiciones)}</textarea></label>
          </div>
        </section>
        <div><button class="btn primario" type="submit">Guardar ajustes</button></div>
      </form>

      <section class="card" style="margin-top:22px">
        <header><h2>Dónde se guardan tus datos</h2></header>
        <div class="cuerpo" style="display:grid;gap:12px">
          <div><div class="small muted">PDF exportados</div><div style="color:var(--ink);word-break:break-all">${esc(info.documentos)}</div></div>
          <div><div class="small muted">Base de datos y respaldos automáticos (cada 15 min y al cerrar)</div><div style="color:var(--ink);word-break:break-all">${esc(info.datos)}</div></div>
          <p class="small muted" style="margin:0">Para pasar todo a otra laptop: instala IKA ahí, ciérrala y copia estas dos carpetas al mismo lugar.</p>
          <div><button type="button" class="btn" id="abrir-docs">Abrir carpeta de PDF</button></div>
        </div>
      </section>
    </div>`;

  el.querySelector("#f").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      await api("/ajustes", { method: "PUT", body: datosForm(e.target) });
      toast("Ajustes guardados");
    } catch (err) { falla(err); }
  });
  const refrescarLogo = () => document.querySelectorAll('img[src^="/api/logo"]').forEach((i) => { i.src = `/api/logo?t=${Date.now()}`; });
  el.querySelector("#logo").addEventListener("change", async (e) => {
    const form = new FormData();
    form.append("logo", e.target.files[0]);
    try {
      await api("/logo", { method: "POST", form });
      toast("Logo actualizado");
      refrescarLogo();
      render(el);
    } catch (err) { falla(err); }
  });
  el.querySelector("#abrir-docs").onclick = () => api("/documentos/abrir-carpeta", { method: "POST", body: {} }).catch(falla);
  el.querySelector("#quitar-logo")?.addEventListener("click", async () => {
    await api("/logo", { method: "DELETE" });
    refrescarLogo();
    render(el);
  });
}
