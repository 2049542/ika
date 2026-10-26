# IKA — cotizaciones y notas de entrega de MR INFRATEC

App local y ligera para cotizar, dar seguimiento a lo abierto por cliente,
generar notas de entrega y llevar el inventario interno (productos con
existencias y servicios de personal). Todo se guarda en esta carpeta, así
que funciona igual desde el disco o desde una USB.

Toma lo que funcionó del sistema anterior (`MR Cotizaciones`): Python +
Flask + SQLite, PDF con reportlab (sin navegador embebido), backups
automáticos y ejecutable portable. Sin frameworks de frontend ni fuentes
descargadas.

## Abrir IKA

Doble clic en **`iniciar.bat`**. Se abre `http://localhost:4580` en el
navegador. No cierres la ventana negra mientras uses la app.

## Qué hace

| Pantalla | Para qué |
|---|---|
| **Panel** | Cotizaciones abiertas agrupadas por cliente (monto, antigüedad), por vencer en 5 días, aprobadas del mes, notas por entregar y stock bajo. |
| **Cotizaciones** | Editor tipo SAP: buscas en el inventario, Enter agrega la partida y el cursor queda en la cantidad. Guarda solo. Totales con IVA y descuento por partida, margen estimado interno. |
| **Vista previa** | Muestra el PDF real antes de exportarlo; no cambia el estado ni guarda archivos. |
| **Exportar PDF** | Guarda en `documentos/<Cliente>/Cotizaciones/<Cliente> - <Folio>.pdf`. Un borrador exportado pasa a *Enviada*. |
| **Notas de entrega** | Se crean desde una cotización (menú ⋯) o desde cero. Al marcarlas *Entregada* descuentan existencias; si se regresan a pendiente, las devuelven. PDF con casillas de recibido y firmas. |
| **Clientes** | Historial por cliente: abiertas, aprobado, notas y todos sus PDF. Botón para abrir su carpeta. |
| **Inventario** | Productos (con entradas, salidas y ajuste de conteo) y servicios/personal por hora, jornada o día. Colores de categoría tomados del logo MR. |
| **Documentos** | Todos los PDF exportados, agrupados por cliente. |
| **Ajustes** | Datos de la empresa y firma para los PDF, logo, IVA, vigencia, prefijos de folio y condiciones por defecto. |

Los folios son `MR-2026-001` para cotizaciones y `NE-2026-001` para notas
(prefijos editables en Ajustes). Una cotización enviada cuya vigencia ya pasó
se marca *Vencida* sola.

## Dónde quedan los datos

```
IKA/
├── iniciar.bat          abrir la app
├── build.bat            genera app/IKA.exe (portable, sin Python)
├── data/ika.db          base de datos (SQLite)
├── backups/             copia al abrir, cada 15 min y al cerrar (últimas 15)
├── documentos/          PDF exportados, una carpeta por cliente
├── backend/             código Python (Flask, API, PDFs)
└── frontend/            HTML/CSS/JS sin build
```

El inventario arranca con algunos artículos y servicios de personal de
ejemplo (técnico, ayudante, ingeniero, supervisión…) con precios de
referencia: ajústalos o bórralos en **Inventario**.

## Desarrollo

```powershell
py -m venv backend\venv
backend\venv\Scripts\pip install -r requirements.txt
backend\venv\Scripts\python.exe backend\app.py
```

Cambios en `frontend/` se ven recargando el navegador; cambios en
`backend/*.py` requieren reiniciar el servidor. Variables útiles:
`IKA_PUERTO` (por defecto 4580) e `IKA_RAIZ` (carpeta de datos alternativa,
para pruebas).

Para llevarlo a otra computadora o USB: corre `build.bat` una vez y copia
`iniciar.bat`, `app/`, `data/`, `backups/` y `documentos/`.
