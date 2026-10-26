// Utilidades compartidas: API, formato, plantillas, avisos y diálogos.

export async function api(ruta, { method = "GET", body, form } = {}) {
  const opts = { method, headers: {} };
  if (form) opts.body = form;
  else if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const r = await fetch(`/api${ruta}`, opts);
  const datos = r.headers.get("content-type")?.includes("json") ? await r.json() : null;
  if (!r.ok) throw new Error(datos?.error || `Error ${r.status}`);
  return datos;
}

export const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

const fmtDinero = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
const fmtCorto = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 });
const fmtNum = new Intl.NumberFormat("es-MX", { maximumFractionDigits: 2 });
export const dinero = (v) => fmtDinero.format(v || 0);
export const dineroCorto = (v) => fmtCorto.format(v || 0);
export const num = (v) => fmtNum.format(v || 0);

export function fecha(iso, conAnio = false) {
  if (!iso) return "";
  const d = new Date(String(iso).slice(0, 10) + "T12:00:00");
  return d.toLocaleDateString("es-MX", { day: "numeric", month: "short", ...(conAnio ? { year: "numeric" } : {}) });
}

export function hace(dias) {
  if (dias <= 0) return "hoy";
  if (dias === 1) return "ayer";
  return `hace ${dias} días`;
}

export const ESTADOS = {
  borrador: "Borrador", enviada: "Enviada", aprobada: "Aprobada", rechazada: "Rechazada", vencida: "Vencida",
  pendiente: "Por entregar", entregada: "Entregada",
};
export const CATEGORIAS = { energia: "Energía", cctv: "CCTV", red: "Redes", personal: "Personal", otro: "Otro" };

export const pill = (estado) => `<span class="pill e-${estado}">${ESTADOS[estado] || estado}</span>`;
export const cat = (c) => `<span class="cat cat-${c}">${CATEGORIAS[c] || c}</span>`;
export const icono = (id) => `<svg aria-hidden="true"><use href="#i-${id}"/></svg>`;

export function vacio(titulo, texto, accion = "") {
  return `<div class="vacio"><b>${titulo}</b>${texto}${accion ? `<div style="margin-top:14px">${accion}</div>` : ""}</div>`;
}

export function toast(texto, { error = false, html = false, ms = 3200 } = {}) {
  const el = document.createElement("div");
  el.className = "toast" + (error ? " error" : "");
  el.setAttribute("role", error ? "alert" : "status");
  if (html) el.innerHTML = texto; else el.textContent = texto;
  document.getElementById("toasts").append(el);
  setTimeout(() => { el.classList.add("sale"); setTimeout(() => el.remove(), 220); }, ms);
}

export const falla = (e) => toast(e.message || String(e), { error: true, ms: 5000 });

export function debounce(fn, ms) {
  let t;
  const d = (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
  d.ahora = (...a) => { clearTimeout(t); return fn(...a); };
  return d;
}

// Diálogo genérico. `cuerpo` es HTML; `alAceptar(form)` puede devolver false para no cerrar.
export function dialogo({ titulo, cuerpo, aceptar = "Guardar", peligro = false, alAceptar, clase = "", sinPie = false }) {
  const d = document.createElement("dialog");
  d.className = clase;
  d.innerHTML = `
    <form method="dialog">
      <header><h2>${titulo}</h2><button type="button" class="btn fantasma icono" data-cerrar aria-label="Cerrar">${icono("x")}</button></header>
      <div class="cuerpo">${cuerpo}</div>
      ${sinPie ? "" : `<footer>
        <button type="button" class="btn fantasma" data-cerrar>Cancelar</button>
        <button type="submit" class="btn primario${peligro ? " peligro" : ""}" value="ok">${aceptar}</button>
      </footer>`}
    </form>`;
  document.body.append(d);
  const form = d.querySelector("form");
  d.querySelectorAll("[data-cerrar]").forEach((b) => b.addEventListener("click", () => d.close()));
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try {
      const r = alAceptar ? await alAceptar(form, d) : true;
      if (r !== false) d.close();
    } catch (e) { falla(e); }
  });
  d.addEventListener("close", () => d.remove());
  d.showModal();
  d.querySelector("input, select, textarea")?.focus();
  return d;
}

export function confirmar(titulo, texto, aceptar = "Confirmar") {
  return new Promise((ok) => {
    let si = false;
    const d = dialogo({ titulo, cuerpo: `<p style="margin:0">${texto}</p>`, aceptar, alAceptar: () => { si = true; } });
    d.addEventListener("close", () => ok(si));
  });
}

// Vista previa: el PDF real, generado al vuelo, sin guardarlo ni cambiar el estado.
export function visor(titulo, url, acciones = "") {
  const d = dialogo({
    titulo, clase: "visor", sinPie: true,
    cuerpo: "",
  });
  const header = d.querySelector("header");
  header.querySelector("[data-cerrar]").insertAdjacentHTML("beforebegin", acciones);
  d.querySelector(".cuerpo").remove();
  const marco = document.createElement("iframe");
  marco.title = titulo;
  marco.src = `${url}?t=${Date.now()}#view=FitH`;
  d.querySelector("form").after(marco);
  d.querySelector("form").style.display = "contents";
  return d;
}

export const datosForm = (form) => Object.fromEntries(new FormData(form).entries());

// Menú desplegable simple (botón + lista).
export function menu(boton, lista) {
  const cerrar = (ev) => {
    if (ev && lista.contains(ev.target) && ev.target.tagName !== "BUTTON") return;
    lista.hidden = true;
    document.removeEventListener("click", cerrar, true);
  };
  boton.addEventListener("click", () => {
    lista.hidden = !lista.hidden;
    if (!lista.hidden) setTimeout(() => document.addEventListener("click", cerrar, true));
  });
}
