-- IKA — esquema SQLite. Seguro de correr en cada arranque (IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS clientes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  nombre      TEXT NOT NULL,
  rfc         TEXT,
  contacto    TEXT,
  telefono    TEXT,
  email       TEXT,
  direccion   TEXT,
  notas       TEXT,
  creado      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Inventario interno: productos (con existencias) y servicios (personal,
-- mano de obra, viáticos...) que no llevan existencias.
CREATE TABLE IF NOT EXISTS inventario (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  sku           TEXT,
  nombre        TEXT NOT NULL,
  descripcion   TEXT,
  tipo          TEXT NOT NULL DEFAULT 'producto' CHECK (tipo IN ('producto','servicio')),
  categoria     TEXT NOT NULL DEFAULT 'otro'
                  CHECK (categoria IN ('energia','cctv','red','personal','otro')),
  unidad        TEXT NOT NULL DEFAULT 'pza',
  costo         REAL NOT NULL DEFAULT 0,
  precio        REAL NOT NULL DEFAULT 0,
  stock         REAL NOT NULL DEFAULT 0,
  stock_minimo  REAL NOT NULL DEFAULT 0,
  activo        INTEGER NOT NULL DEFAULT 1,
  actualizado   TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS movimientos (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  inventario_id  INTEGER NOT NULL REFERENCES inventario(id) ON DELETE CASCADE,
  tipo           TEXT NOT NULL CHECK (tipo IN ('entrada','salida','ajuste')),
  cantidad       REAL NOT NULL,
  referencia     TEXT,
  fecha          TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS cotizaciones (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  folio           TEXT NOT NULL UNIQUE,
  cliente_id      INTEGER REFERENCES clientes(id),
  titulo          TEXT,
  estado          TEXT NOT NULL DEFAULT 'borrador'
                    CHECK (estado IN ('borrador','enviada','aprobada','rechazada','vencida')),
  fecha           TEXT NOT NULL DEFAULT (date('now','localtime')),
  vigencia_dias   INTEGER NOT NULL DEFAULT 15,
  tiempo_entrega  TEXT,
  forma_pago      TEXT,
  condiciones     TEXT,
  notas_internas  TEXT,
  iva_pct         REAL NOT NULL DEFAULT 16,
  subtotal        REAL NOT NULL DEFAULT 0,
  descuento       REAL NOT NULL DEFAULT 0,
  iva             REAL NOT NULL DEFAULT 0,
  total           REAL NOT NULL DEFAULT 0,
  creada          TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  actualizada     TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  eliminada       INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cotizacion_items (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  cotizacion_id    INTEGER NOT NULL REFERENCES cotizaciones(id) ON DELETE CASCADE,
  inventario_id    INTEGER REFERENCES inventario(id) ON DELETE SET NULL,
  sku              TEXT,
  descripcion      TEXT NOT NULL,
  unidad           TEXT NOT NULL DEFAULT 'pza',
  cantidad         REAL NOT NULL DEFAULT 1,
  precio_unitario  REAL NOT NULL DEFAULT 0,
  descuento_pct    REAL NOT NULL DEFAULT 0,
  orden            INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS notas_entrega (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  folio              TEXT NOT NULL UNIQUE,
  cliente_id         INTEGER REFERENCES clientes(id),
  cotizacion_id      INTEGER REFERENCES cotizaciones(id) ON DELETE SET NULL,
  estado             TEXT NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','entregada')),
  fecha              TEXT NOT NULL DEFAULT (date('now','localtime')),
  direccion_entrega  TEXT,
  recibe             TEXT,
  observaciones      TEXT,
  stock_descontado   INTEGER NOT NULL DEFAULT 0,
  creada             TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  actualizada        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  eliminada          INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS nota_items (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  nota_id        INTEGER NOT NULL REFERENCES notas_entrega(id) ON DELETE CASCADE,
  inventario_id  INTEGER REFERENCES inventario(id) ON DELETE SET NULL,
  sku            TEXT,
  descripcion    TEXT NOT NULL,
  unidad         TEXT NOT NULL DEFAULT 'pza',
  cantidad       REAL NOT NULL DEFAULT 1,
  orden          INTEGER NOT NULL DEFAULT 0
);

-- Cada PDF exportado queda registrado aquí (ruta relativa a /documentos).
CREATE TABLE IF NOT EXISTS documentos (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tipo        TEXT NOT NULL CHECK (tipo IN ('cotizacion','nota')),
  ref_id      INTEGER NOT NULL,
  cliente_id  INTEGER REFERENCES clientes(id),
  folio       TEXT NOT NULL,
  archivo     TEXT NOT NULL,
  creado      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS configuracion (
  clave  TEXT PRIMARY KEY,
  valor  TEXT
);

CREATE INDEX IF NOT EXISTS idx_cot_estado ON cotizaciones(estado, eliminada);
CREATE INDEX IF NOT EXISTS idx_cot_cliente ON cotizaciones(cliente_id);
CREATE INDEX IF NOT EXISTS idx_nota_cliente ON notas_entrega(cliente_id);
CREATE INDEX IF NOT EXISTS idx_docs_cliente ON documentos(cliente_id);

INSERT OR IGNORE INTO configuracion (clave, valor) VALUES
  ('empresa_nombre',   'MR INFRATEC'),
  ('empresa_lema',     'Energía · CCTV · Redes'),
  ('empresa_telefono', '+52 81 4815 3047'),
  ('empresa_email',    ''),
  ('empresa_web',      ''),
  ('empresa_direccion',''),
  ('empresa_rfc',      ''),
  ('prefijo_cotizacion','MR'),
  ('prefijo_nota',     'NE'),
  ('iva_pct',          '16'),
  ('vigencia_dias',    '15'),
  ('forma_pago',       '50% anticipo, 50% contra entrega'),
  ('tiempo_entrega',   '5 a 7 días hábiles'),
  ('condiciones',      'Precios en pesos mexicanos (MXN). La vigencia corre a partir de la fecha de la cotización. Los servicios de instalación incluyen mano de obra y pruebas; materiales adicionales no listados se cotizan por separado.'),
  ('firma_nombre',     ''),
  ('firma_puesto',     '');
