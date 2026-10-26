// Router por hash. Cada vista exporta `render(el, params)` y puede devolver
// una función de limpieza que se llama al salir.
import { api, falla } from "./core.js";
import * as panel from "./vistas/panel.js";
import * as cotizaciones from "./vistas/cotizaciones.js";
import * as notas from "./vistas/notas.js";
import * as clientes from "./vistas/clientes.js";
import * as inventario from "./vistas/inventario.js";
import * as documentos from "./vistas/documentos.js";
import * as ajustes from "./vistas/ajustes.js";

const rutas = [
  [/^\/?$/, "panel", panel.render],
  [/^\/cotizaciones$/, "cotizaciones", cotizaciones.lista],
  [/^\/cotizacion\/(\d+)$/, "cotizaciones", cotizaciones.editor],
  [/^\/notas$/, "notas", notas.lista],
  [/^\/nota\/(\d+)$/, "notas", notas.editor],
  [/^\/clientes$/, "clientes", clientes.lista],
  [/^\/cliente\/(\d+)$/, "clientes", clientes.detalle],
  [/^\/inventario$/, "inventario", inventario.render],
  [/^\/documentos$/, "documentos", documentos.render],
  [/^\/ajustes$/, "ajustes", ajustes.render],
];

const vista = document.getElementById("vista");
let limpiar = null;

async function navegar() {
  const ruta = location.hash.replace(/^#/, "").split("?")[0] || "/";
  const [m, nombre, fn] = rutas.map(([re, n, f]) => [ruta.match(re), n, f]).find(([m]) => m)
    || [[""], "panel", panel.render];
  const params = m.slice(1);

  document.querySelectorAll(".nav a").forEach((a) => {
    if (a.dataset.ruta === nombre) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });

  document.querySelectorAll("dialog[open]").forEach((d) => d.close());
  if (typeof limpiar === "function") await limpiar();
  limpiar = null;
  vista.innerHTML = "";
  window.scrollTo(0, 0);
  try {
    limpiar = await fn(vista, ...params);
  } catch (e) {
    vista.innerHTML = `<div class="vacio"><b>No se pudo abrir esta pantalla</b>${e.message}</div>`;
  }
  contadores();
}

export async function contadores() {
  try {
    const p = await api("/panel");
    const set = (id, n) => {
      const el = document.getElementById(id);
      el.textContent = n;
      el.hidden = !n;
    };
    set("n-abiertas", p.abiertas.n);
    set("n-notas", p.notas_pendientes.length);
  } catch { /* el servidor puede estar cerrándose */ }
}

export const ir = (hash) => { location.hash = hash; };

// Señal de vida: si IKA se abrió en un navegador normal (sin Edge), el
// servidor se apaga solo unos minutos después de cerrar la pestaña.
const latido = () => fetch("/api/latido", { method: "POST" }).catch(() => {});
latido();
setInterval(latido, 20000);

window.addEventListener("hashchange", navegar);
window.addEventListener("unhandledrejection", (e) => falla(e.reason));
navegar();
