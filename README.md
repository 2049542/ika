# IKA — cotizaciones y notas de entrega de MR INFRATEC

App de escritorio para Windows, ligera y sin internet, para cotizar, dar
seguimiento a lo abierto por cliente, generar notas de entrega y llevar el
inventario interno (productos con existencias y servicios de personal).

Toma lo que funcionó del sistema anterior (`MR Cotizaciones`): Python +
Flask + SQLite, PDF con reportlab (sin navegador embebido), backups
automáticos y ejecutable portable. Sin frameworks de frontend ni fuentes
descargadas.

## Instalar en una laptop

1. Copia **`IKA-Instalador.exe`** a la laptop (USB, correo, Drive…). Lo genera
   `build.bat` en la carpeta `app/`.
2. Dale doble clic. No pide permisos de administrador ni internet.
   - Windows puede mostrar *"Windows protegió su PC"* porque el instalador no
     está firmado: **Más información → Ejecutar de todas formas**.
3. Queda un acceso directo **IKA** en el Escritorio y en el menú Inicio.

IKA se abre en su propia ventana (sin pestañas ni consola). Al cerrar la
ventana, guarda un respaldo y se apaga sola. Si se abre dos veces, reutiliza
la que ya está corriendo. Funciona en Windows 10 y 11 sin internet.

**Actualizar:** se corre el instalador nuevo encima; los datos se conservan.
**Desinstalar:** menú Inicio → IKA → *Desinstalar IKA*. También conserva los
datos y avisa dónde quedaron.

**Sin instalar (USB):** descomprime `IKA-Portable.zip` en la USB y abre
`IKA\IKA.exe`. En este modo los datos y PDF se guardan dentro de esa carpeta.

## Qué hace

| Pantalla | Para qué |
|---|---|
| **Panel** | Cotizaciones abiertas agrupadas por cliente (monto, antigüedad), por vencer en 5 días, aprobadas del mes, notas por entregar y stock bajo. |
| **Cotizaciones** | Editor tipo SAP: buscas en el inventario, Enter agrega la partida y el cursor queda en la cantidad. Guarda solo. Totales con IVA y descuento por partida, margen estimado interno. |
| **Vista previa** | Muestra el PDF real antes de exportarlo; no cambia el estado ni guarda archivos. |
| **Exportar PDF** | Guarda en `Documentos\IKA\<Cliente>\Cotizaciones\<Cliente> - <Folio>.pdf`. Un borrador exportado pasa a *Enviada*. |
| **Notas de entrega** | Se crean desde una cotización (menú ⋯) o desde cero. Al marcarlas *Entregada* descuentan existencias; si se regresan a pendiente, las devuelven. PDF con casillas de recibido y firmas. |
| **Clientes** | Historial por cliente: abiertas, aprobado, notas y todos sus PDF. Botón para abrir su carpeta. |
| **Inventario** | Productos (con entradas, salidas y ajuste de conteo) y servicios/personal por hora, jornada o día. Colores de categoría tomados del logo MR. |
| **Documentos** | Todos los PDF exportados, agrupados por cliente. |
| **Ajustes** | Datos de la empresa y firma para los PDF, logo, IVA, vigencia, prefijos de folio y condiciones por defecto. |

Los folios son `MR-2026-001` para cotizaciones y `NE-2026-001` para notas
(prefijos editables en Ajustes). Una cotización enviada cuya vigencia ya pasó
se marca *Vencida* sola.

## Dónde quedan los datos

En una laptop con IKA instalada (también se ve en **Ajustes**):

| Qué | Dónde |
|---|---|
| PDF exportados | `Documentos\IKA\<Cliente>\...` |
| Base de datos, respaldos y registro | `%LOCALAPPDATA%\IKA\` (respaldo al abrir, cada 15 min y al cerrar; se guardan los últimos 15) |
| Programa | `%LOCALAPPDATA%\Programs\IKA\` |

Cada laptop tiene sus propios datos. Para pasarlos a otra: instala IKA ahí,
ciérrala y copia esas dos carpetas de datos al mismo lugar.

El inventario arranca con algunos artículos y servicios de personal de
ejemplo (técnico, ayudante, ingeniero, supervisión…) con precios de
referencia: ajústalos o bórralos en **Inventario**.

## Desarrollo

```
IKA/
├── backend/        Flask + SQLite + PDF (app.py arranca servidor y ventana)
├── frontend/       HTML/CSS/JS sin build
├── instalador/     instalar.py e ícono
├── build.bat       genera app/IKA-Instalador.exe y app/IKA-Portable.zip
└── iniciar.bat     abre IKA con el Python del proyecto (desarrollo)
```

```powershell
py -m venv backend\venv
backend\venv\Scripts\pip install -r requirements.txt
backend\venv\Scripts\python.exe backend\app.py             # con ventana
backend\venv\Scripts\python.exe backend\app.py --servidor  # solo servidor
```

En desarrollo los datos van a `data/`, `backups/` y `documentos/` dentro del
repo (ignorados por git). Variables útiles: `IKA_PUERTO` (4580 por defecto),
`IKA_RAIZ` (otra carpeta para todos los datos, para pruebas) e
`IKA_VENTANA=navegador` (abre en el navegador normal en vez de la ventana de
Edge; el servidor se apaga unos minutos después de cerrar la pestaña).

Después de cambiar código, vuelve a correr `build.bat` para generar un
instalador nuevo.
