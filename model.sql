-- ==========================================================
-- DUACYD ANALÍTICA - ESQUEMA COMPLETO (MySQL 8+)
-- ==========================================================
SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- (Opcional) Para recrear limpio:
-- SET FOREIGN_KEY_CHECKS = 0;
-- DROP DATABASE IF EXISTS duacyd_analitica;
-- SET FOREIGN_KEY_CHECKS = 1;

CREATE DATABASE IF NOT EXISTS duacyd_analitica
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;
USE duacyd_analitica;

-- ==========================
-- 1) SEGURIDAD / ACCESOS
-- ==========================
CREATE TABLE rol (
  id_rol INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(50) NOT NULL UNIQUE,     -- Administrador, Jefatura, Analista, Lector
  descripcion VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE permiso (
  id_permiso INT AUTO_INCREMENT PRIMARY KEY,
  clave VARCHAR(100) NOT NULL UNIQUE,     -- ej. ver_dashboard, cargar_datos, administrar_catalogos
  descripcion VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE rol_permiso (
  id_rol INT NOT NULL,
  id_permiso INT NOT NULL,
  PRIMARY KEY (id_rol, id_permiso),
  FOREIGN KEY (id_rol) REFERENCES rol(id_rol),
  FOREIGN KEY (id_permiso) REFERENCES permiso(id_permiso)
) ENGINE=InnoDB;

CREATE TABLE usuario (
  id_usuario INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  apellidos VARCHAR(100) NOT NULL,
  correo VARCHAR(150) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  activo TINYINT(1) NOT NULL DEFAULT 1,
  ultimo_login TIMESTAMP NULL,
  fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE usuario_rol (
  id_usuario INT NOT NULL,
  id_rol INT NOT NULL,
  PRIMARY KEY (id_usuario, id_rol),
  FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
  FOREIGN KEY (id_rol) REFERENCES rol(id_rol)
) ENGINE=InnoDB;

-- =================================
-- 2) ESTRUCTURA ORGANIZACIONAL
-- =================================
CREATE TABLE area (
  id_area INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(50) NOT NULL UNIQUE,     -- SUAYED, EDCO, CLE
  descripcion VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE jefatura (
  id_jefatura INT AUTO_INCREMENT PRIMARY KEY,
  id_area INT NOT NULL,
  nombre VARCHAR(120) NOT NULL,
  descripcion VARCHAR(255),
  UNIQUE KEY uq_jef_area (id_area, nombre),
  FOREIGN KEY (id_area) REFERENCES area(id_area)
) ENGINE=InnoDB;

-- Carreras solo aplican a SUAYED
CREATE TABLE carrera (
  id_carrera INT AUTO_INCREMENT PRIMARY KEY,
  id_area INT NOT NULL,                   -- Debe ser SUAYED
  nombre VARCHAR(120) NOT NULL,
  descripcion VARCHAR(255),
  UNIQUE KEY uq_carrera_area (id_area, nombre),
  FOREIGN KEY (id_area) REFERENCES area(id_area)
) ENGINE=InnoDB;

-- Accesos por área/carrera (scoping de datos por usuario)
CREATE TABLE usuario_area (
  id_usuario INT NOT NULL,
  id_area INT NOT NULL,
  PRIMARY KEY (id_usuario, id_area),
  FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
  FOREIGN KEY (id_area) REFERENCES area(id_area)
) ENGINE=InnoDB;

CREATE TABLE usuario_carrera (
  id_usuario INT NOT NULL,
  id_carrera INT NOT NULL,
  PRIMARY KEY (id_usuario, id_carrera),
  FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario),
  FOREIGN KEY (id_carrera) REFERENCES carrera(id_carrera)
) ENGINE=InnoDB;

-- =================================
-- 3) CATÁLOGOS (períodos/unidades/etc.)
-- =================================
CREATE TABLE cat_frecuencia (
  id_frecuencia TINYINT AUTO_INCREMENT PRIMARY KEY,
  clave VARCHAR(20) NOT NULL UNIQUE,      -- mensual, trimestral, semestral, anual
  descripcion VARCHAR(120)
) ENGINE=InnoDB;

CREATE TABLE cat_unidad (
  id_unidad TINYINT AUTO_INCREMENT PRIMARY KEY,
  clave VARCHAR(20) NOT NULL UNIQUE,      -- numero, %, mxn, horas, cursos
  descripcion VARCHAR(120)
) ENGINE=InnoDB;

-- Periodo flexible (clave puede ser '2025-1', '2025-08', '2025Q3', '2025')
CREATE TABLE periodo (
  id_periodo INT AUTO_INCREMENT PRIMARY KEY,
  clave VARCHAR(20) NOT NULL UNIQUE,      -- etiqueta visible
  anio SMALLINT NOT NULL,
  mes TINYINT NULL,                        -- 1-12, opcional
  trimestre TINYINT NULL,                  -- 1-4, opcional
  semestre TINYINT NULL,                   -- 1-2, opcional
  id_frecuencia TINYINT NOT NULL,
  fecha_inicio DATE NULL,
  fecha_fin DATE NULL,
  FOREIGN KEY (id_frecuencia) REFERENCES cat_frecuencia(id_frecuencia),
  CHECK (semestre IN (1,2) OR semestre IS NULL),
  CHECK (trimestre BETWEEN 1 AND 4 OR trimestre IS NULL),
  CHECK (mes BETWEEN 1 AND 12 OR mes IS NULL)
) ENGINE=InnoDB;

-- =================================
-- 4) INDICADORES Y METAS
-- =================================
CREATE TABLE fuente_dato (
  id_fuente INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL UNIQUE,     -- SIGA, Kardex, PASD, Encuesta, etc.
  descripcion VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE categoria_indicador (
  id_categoria INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(120) NOT NULL UNIQUE,     -- Productividad, Cobertura, Calidad, Ingresos, etc.
  descripcion VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE indicador (
  id_indicador INT AUTO_INCREMENT PRIMARY KEY,
  id_area INT NOT NULL,
  id_jefatura INT NULL,
  id_categoria INT NULL,
  clave VARCHAR(50) NOT NULL UNIQUE,       -- EJ: MATRICULA_TOTAL, TASA_EGRESO
  nombre VARCHAR(200) NOT NULL,
  descripcion TEXT,
  formula TEXT,
  id_unidad TINYINT NOT NULL,
  id_frecuencia TINYINT NOT NULL,          -- frecuencia de reporte esperada
  id_fuente INT NULL,
  requiere_carrera TINYINT(1) NOT NULL DEFAULT 0,   -- 1 si desglosa por carrera (SUAYED)
  activo TINYINT(1) NOT NULL DEFAULT 1,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_area) REFERENCES area(id_area),
  FOREIGN KEY (id_jefatura) REFERENCES jefatura(id_jefatura),
  FOREIGN KEY (id_categoria) REFERENCES categoria_indicador(id_categoria),
  FOREIGN KEY (id_unidad) REFERENCES cat_unidad(id_unidad),
  FOREIGN KEY (id_frecuencia) REFERENCES cat_frecuencia(id_frecuencia),
  FOREIGN KEY (id_fuente) REFERENCES fuente_dato(id_fuente)
) ENGINE=InnoDB;

CREATE TABLE meta_indicador (
  id_meta INT AUTO_INCREMENT PRIMARY KEY,
  id_indicador INT NOT NULL,
  id_periodo INT NOT NULL,
  id_carrera INT NULL,                     -- si la meta aplica por carrera
  valor_meta DECIMAL(18,4) NOT NULL,
  comentario VARCHAR(255),
  UNIQUE KEY uq_meta (id_indicador, id_periodo, id_carrera),
  FOREIGN KEY (id_indicador) REFERENCES indicador(id_indicador),
  FOREIGN KEY (id_periodo) REFERENCES periodo(id_periodo),
  FOREIGN KEY (id_carrera) REFERENCES carrera(id_carrera)
) ENGINE=InnoDB;

-- =================================
-- 5) HECHOS (VALORES) + INGESTA
-- =================================
CREATE TABLE lote_carga (
  id_lote BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_area INT NOT NULL,
  id_usuario INT NOT NULL,
  origen VARCHAR(120) NULL,                 -- manual, csv, xlsx, API
  descripcion VARCHAR(255) NULL,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_area) REFERENCES area(id_area),
  FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
) ENGINE=InnoDB;

CREATE TABLE archivo_cargado (
  id_archivo BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_lote BIGINT NOT NULL,
  nombre_archivo VARCHAR(255) NOT NULL,
  tipo_archivo VARCHAR(40) NOT NULL,        -- csv, xlsx, pdf
  ruta VARCHAR(600) NULL,                   -- path si aplica
  filas_ok INT NOT NULL DEFAULT 0,
  filas_error INT NOT NULL DEFAULT 0,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_lote) REFERENCES lote_carga(id_lote)
) ENGINE=InnoDB;

CREATE TABLE error_carga (
  id_error BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_archivo BIGINT NOT NULL,
  num_fila INT NOT NULL,
  mensaje VARCHAR(500) NOT NULL,
  payload_json JSON NULL,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_archivo) REFERENCES archivo_cargado(id_archivo)
) ENGINE=InnoDB;

-- Fact table de valores por indicador
CREATE TABLE valor_indicador (
  id_valor BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_indicador INT NOT NULL,
  id_periodo INT NOT NULL,
  id_area INT NOT NULL,                     -- redundante para acelerar queries (ajustado por trigger)
  id_carrera INT NULL,                      -- solo si requiere_carrera=1 y área=SUAYED
  valor DECIMAL(18,4) NOT NULL,
  nota VARCHAR(255) NULL,
  id_lote BIGINT NULL,
  id_usuario INT NOT NULL,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- Para garantizar unicidad con NULL, usamos columna generada
  carrera_key INT GENERATED ALWAYS AS (IFNULL(id_carrera, 0)) STORED,
  UNIQUE KEY uq_valor (id_indicador, id_periodo, carrera_key),
  INDEX ix_valor_periodo (id_periodo),
  INDEX ix_valor_area (id_area),
  FOREIGN KEY (id_indicador) REFERENCES indicador(id_indicador),
  FOREIGN KEY (id_periodo) REFERENCES periodo(id_periodo),
  FOREIGN KEY (id_carrera) REFERENCES carrera(id_carrera),
  FOREIGN KEY (id_lote) REFERENCES lote_carga(id_lote),
  FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
) ENGINE=InnoDB;

-- Tabla de archivos fuente (para consulta/descarga posterior)
CREATE TABLE archivo_fuente (
  id_fuente_archivo BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_area INT NOT NULL,
  id_carrera INT NULL,
  nombre_archivo VARCHAR(255) NOT NULL,
  ruta VARCHAR(600) NOT NULL,
  tipo_archivo VARCHAR(40),
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  id_usuario INT NOT NULL,
  FOREIGN KEY (id_area) REFERENCES area(id_area),
  FOREIGN KEY (id_carrera) REFERENCES carrera(id_carrera),
  FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
) ENGINE=InnoDB;

-- =================================
-- 6) BITÁCORA
-- =================================
CREATE TABLE log_actividad (
  id_log BIGINT AUTO_INCREMENT PRIMARY KEY,
  id_usuario INT NOT NULL,
  accion VARCHAR(200) NOT NULL,             -- "carga_indicador", "actualiza_meta", "sube_archivo"
  detalle TEXT,
  creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)
) ENGINE=InnoDB;

-- =================================
-- 7) TRIGGERS DE INTEGRIDAD
-- =================================
DELIMITER $$

-- Asegura que id_area se derive del indicador y valida reglas de carrera/SUAYED
CREATE TRIGGER trg_valor_indicador_bi
BEFORE INSERT ON valor_indicador
FOR EACH ROW
BEGIN
  DECLARE v_area INT;
  DECLARE v_req_carrera TINYINT;
  DECLARE v_carr_area INT;
  SELECT id_area, requiere_carrera INTO v_area, v_req_carrera
  FROM indicador WHERE id_indicador = NEW.id_indicador;

  SET NEW.id_area = v_area;  -- forzamos consistencia

  -- Si requiere carrera y no hay carrera -> error
  IF v_req_carrera = 1 AND NEW.id_carrera IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El indicador requiere id_carrera (SUAYED).';
  END IF;

  -- Si NO requiere carrera y viene una carrera -> normalizamos a NULL
  IF v_req_carrera = 0 AND NEW.id_carrera IS NOT NULL THEN
    SET NEW.id_carrera = NULL;
  END IF;

  -- Si hay carrera, debe pertenecer a SUAYED (id_area=1 por seed; o mejor validamos por la carrera misma)
  IF NEW.id_carrera IS NOT NULL THEN
    SELECT id_area INTO v_carr_area FROM carrera WHERE id_carrera = NEW.id_carrera;
    IF v_carr_area <> v_area THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La carrera no pertenece al área del indicador.';
    END IF;
  END IF;
END$$

CREATE TRIGGER trg_valor_indicador_bu
BEFORE UPDATE ON valor_indicador
FOR EACH ROW
BEGIN
  DECLARE v_area INT;
  DECLARE v_req_carrera TINYINT;
  DECLARE v_carr_area INT;
  SELECT id_area, requiere_carrera INTO v_area, v_req_carrera
  FROM indicador WHERE id_indicador = NEW.id_indicador;

  SET NEW.id_area = v_area;

  IF v_req_carrera = 1 AND NEW.id_carrera IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'El indicador requiere id_carrera (SUAYED).';
  END IF;

  IF v_req_carrera = 0 AND NEW.id_carrera IS NOT NULL THEN
    SET NEW.id_carrera = NULL;
  END IF;

  IF NEW.id_carrera IS NOT NULL THEN
    SELECT id_area INTO v_carr_area FROM carrera WHERE id_carrera = NEW.id_carrera;
    IF v_carr_area <> v_area THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'La carrera no pertenece al área del indicador.';
    END IF;
  END IF;
END$$
DELIMITER ;

-- =================================
-- 8) STORED PROCEDURE: UPSERT DE VALOR
-- =================================
DELIMITER $$
CREATE PROCEDURE sp_upsert_valor_indicador (
  IN p_id_indicador INT,
  IN p_id_periodo INT,
  IN p_id_carrera INT,           -- puede ser NULL si no aplica
  IN p_valor DECIMAL(18,4),
  IN p_id_usuario INT,
  IN p_id_lote BIGINT            -- puede ser NULL
)
BEGIN
  DECLARE v_carrera_key INT;
  SET v_carrera_key = IFNULL(p_id_carrera, 0);

  -- Intento de UPDATE por clave natural
  UPDATE valor_indicador
     SET valor = p_valor,
         id_lote = p_id_lote,
         id_usuario = p_id_usuario
   WHERE id_indicador = p_id_indicador
     AND id_periodo   = p_id_periodo
     AND carrera_key  = v_carrera_key;

  IF ROW_COUNT() = 0 THEN
    INSERT INTO valor_indicador (id_indicador, id_periodo, id_area, id_carrera, valor, id_lote, id_usuario)
    VALUES (
      p_id_indicador, p_id_periodo,
      0,                   -- se corrige por trigger
      p_id_carrera, p_valor, p_id_lote, p_id_usuario
    );
  END IF;
END$$
DELIMITER ;

-- =================================
-- 9) VISTAS ÚTILES PARA DASHBOARD
-- =================================
CREATE OR REPLACE VIEW vw_indicadores_recientes AS
SELECT
  i.id_indicador,
  i.clave AS indicador_clave,
  i.nombre AS indicador_nombre,
  a.nombre AS area,
  p.clave AS periodo,
  v.id_carrera,
  c.nombre AS carrera,
  v.valor,
  v.creado_en
FROM valor_indicador v
JOIN indicador i ON i.id_indicador = v.id_indicador
JOIN area a ON a.id_area = v.id_area
JOIN periodo p ON p.id_periodo = v.id_periodo
LEFT JOIN carrera c ON c.id_carrera = v.id_carrera;

CREATE OR REPLACE VIEW vw_suayed_por_carrera AS
SELECT
  p.clave AS periodo,
  c.nombre AS carrera,
  i.clave AS indicador,
  v.valor
FROM valor_indicador v
JOIN indicador i ON i.id_indicador = v.id_indicador
JOIN periodo p ON p.id_periodo = v.id_periodo
JOIN carrera c ON c.id_carrera = v.id_carrera
WHERE v.id_area = (SELECT id_area FROM area WHERE nombre='SUAYED' LIMIT 1);

-- =================================
-- 10) SEED DATA
-- =================================

-- Roles
INSERT INTO rol (nombre, descripcion) VALUES
('Administrador','Acceso total'),
('Jefatura','Gestión de su área'),
('Analista','Carga/consulta indicadores'),
('Lector','Solo lectura')
ON DUPLICATE KEY UPDATE descripcion=VALUES(descripcion);

-- Permisos base
INSERT INTO permiso (clave, descripcion) VALUES
('ver_dashboard','Puede ver paneles'),
('cargar_datos','Puede cargar/editar valores'),
('administrar_catalogos','Puede administrar catálogos'),
('administrar_usuarios','Puede administrar usuarios')
ON DUPLICATE KEY UPDATE descripcion=VALUES(descripcion);

-- Mapear permisos a roles
INSERT IGNORE INTO rol_permiso SELECT r.id_rol, p.id_permiso
FROM rol r CROSS JOIN permiso p
WHERE r.nombre IN ('Administrador');

INSERT IGNORE INTO rol_permiso
SELECT r.id_rol, p.id_permiso
FROM rol r JOIN permiso p ON p.clave IN ('ver_dashboard','cargar_datos')
WHERE r.nombre IN ('Jefatura','Analista');

INSERT IGNORE INTO rol_permiso
SELECT r.id_rol, p.id_permiso
FROM rol r JOIN permiso p ON p.clave IN ('ver_dashboard')
WHERE r.nombre IN ('Lector');

-- Usuario admin (reemplaza password_hash por un hash real, p. ej. bcrypt)
INSERT INTO usuario (nombre, apellidos, correo, password_hash, activo)
VALUES ('Admin','DUACyD','admin@duacyd.mx','$2y$10$REEMPLAZA_ESTE_HASH',1)
ON DUPLICATE KEY UPDATE activo=VALUES(activo);

-- Áreas
INSERT INTO area (nombre, descripcion) VALUES
('SUAYED','Sistema Universidad Abierta y Educación a Distancia'),
('EDCO','Educación Continua'),
('CLE','Centro de Lenguas')
ON DUPLICATE KEY UPDATE descripcion=VALUES(descripcion);

-- Jefaturas (ejemplo)
INSERT INTO jefatura (id_area, nombre, descripcion)
SELECT a.id_area, 'Jefatura '||a.nombre, CONCAT('Jefatura de ', a.nombre)
FROM area a
ON DUPLICATE KEY UPDATE descripcion=VALUES(descripcion);

-- Carreras SUAYED
INSERT INTO carrera (id_area, nombre, descripcion)
SELECT a.id_area, t.nombre, t.descripcion
FROM area a
JOIN (SELECT 'Derecho' AS nombre, 'Licenciatura en Derecho SUAYED' AS descripcion
      UNION ALL SELECT 'Relaciones Internacionales','Licenciatura en Relaciones Internacionales SUAYED'
      UNION ALL SELECT 'Economía','Licenciatura en Economía SUAYED') t
WHERE a.nombre='SUAYED'
ON DUPLICATE KEY UPDATE descripcion=VALUES(descripcion);

-- Relacionar admin a todas las áreas
INSERT IGNORE INTO usuario_area (id_usuario, id_area)
SELECT u.id_usuario, a.id_area
FROM usuario u, area a
WHERE u.correo='admin@duacyd.mx';

-- Frecuencias y unidades
INSERT INTO cat_frecuencia (clave, descripcion) VALUES
('mensual','Reporte mensual'),
('trimestral','Reporte trimestral'),
('semestral','Reporte semestral'),
('anual','Reporte anual')
ON DUPLICATE KEY UPDATE descripcion=VALUES(descripcion);

INSERT INTO cat_unidad (clave, descripcion) VALUES
('numero','Conteo entero'),
('%','Porcentaje'),
('mxn','Pesos mexicanos'),
('horas','Horas'),
('cursos','Número de cursos')
ON DUPLICATE KEY UPDATE descripcion=VALUES(descripcion);

-- Periodos ejemplo (2025S1, 2025S2, 2025, 2025-08)
INSERT INTO periodo (clave, anio, semestre, id_frecuencia, fecha_inicio, fecha_fin)
SELECT '2025-1', 2025, 1, (SELECT id_frecuencia FROM cat_frecuencia WHERE clave='semestral'), '2025-01-01','2025-06-30'
ON DUPLICATE KEY UPDATE fecha_fin=VALUES(fecha_fin);

INSERT INTO periodo (clave, anio, semestre, id_frecuencia, fecha_inicio, fecha_fin)
SELECT '2025-2', 2025, 2, (SELECT id_frecuencia FROM cat_frecuencia WHERE clave='semestral'), '2025-07-01','2025-12-31'
ON DUPLICATE KEY UPDATE fecha_fin=VALUES(fecha_fin);

INSERT INTO periodo (clave, anio, id_frecuencia, fecha_inicio, fecha_fin)
SELECT '2025', 2025, (SELECT id_frecuencia FROM cat_frecuencia WHERE clave='anual'), '2025-01-01','2025-12-31'
ON DUPLICATE KEY UPDATE fecha_fin=VALUES(fecha_fin);

INSERT INTO periodo (clave, anio, mes, id_frecuencia, fecha_inicio, fecha_fin)
SELECT '2025-08', 2025, 8, (SELECT id_frecuencia FROM cat_frecuencia WHERE clave='mensual'), '2025-08-01','2025-08-31'
ON DUPLICATE KEY UPDATE fecha_fin=VALUES(fecha_fin);

-- Fuentes y categorías
INSERT INTO fuente_dato (nombre, descripcion) VALUES
('SIGA','Sistema Institucional'),
('Kardex','Kardex académico'),
('PASD','Programa de Actualización y Superación Docente'),
('Encuesta','Instrumentos de levantamiento')
ON DUPLICATE KEY UPDATE descripcion=VALUES(descripcion);

INSERT INTO categoria_indicador (nombre, descripcion) VALUES
('Cobertura','Población atendida'),
('Productividad','Volumen de actividad'),
('Calidad','Resultados académicos'),
('Finanzas','Ingresos/Egresos')
ON DUPLICATE KEY UPDATE descripcion=VALUES(descripcion);

-- Indicadores ejemplo
INSERT INTO indicador (id_area, id_jefatura, id_categoria, clave, nombre, descripcion, formula, id_unidad, id_frecuencia, id_fuente, requiere_carrera, activo)
SELECT a.id_area,
       (SELECT j.id_jefatura FROM jefatura j WHERE j.id_area=a.id_area LIMIT 1),
       (SELECT id_categoria FROM categoria_indicador WHERE nombre='Cobertura'),
       'MATRICULA_TOTAL',
       'Matrícula total',
       'Total de estudiantes inscritos',
       NULL,
       (SELECT id_unidad FROM cat_unidad WHERE clave='numero'),
       (SELECT id_frecuencia FROM cat_frecuencia WHERE clave='semestral'),
       (SELECT id_fuente FROM fuente_dato WHERE nombre='SIGA'),
       CASE WHEN a.nombre='SUAYED' THEN 1 ELSE 0 END,
       1
FROM area a
ON DUPLICATE KEY UPDATE activo=VALUES(activo);

INSERT INTO indicador (id_area, id_jefatura, id_categoria, clave, nombre, descripcion, formula, id_unidad, id_frecuencia, id_fuente, requiere_carrera, activo)
SELECT (SELECT id_area FROM area WHERE nombre='SUAYED'),
       (SELECT j.id_jefatura FROM jefatura j JOIN area a ON a.id_area=j.id_area AND a.nombre='SUAYED' LIMIT 1),
       (SELECT id_categoria FROM categoria_indicador WHERE nombre='Calidad'),
       'TASA_EGRESO',
       'Tasa de egreso',
       'Egresados / Cohorte * 100',
       '(egresados/cohorte)*100',
       (SELECT id_unidad FROM cat_unidad WHERE clave='%'),
       (SELECT id_frecuencia FROM cat_frecuencia WHERE clave='anual'),
       (SELECT id_fuente FROM fuente_dato WHERE nombre='SIGA'),
       1,
       1
ON DUPLICATE KEY UPDATE activo=VALUES(activo);

INSERT INTO indicador (id_area, id_jefatura, id_categoria, clave, nombre, descripcion, formula, id_unidad, id_frecuencia, id_fuente, requiere_carrera, activo)
SELECT (SELECT id_area FROM area WHERE nombre='EDCO'),
       (SELECT j.id_jefatura FROM jefatura j JOIN area a ON a.id_area=j.id_area AND a.nombre='EDCO' LIMIT 1),
       (SELECT id_categoria FROM categoria_indicador WHERE nombre='Finanzas'),
       'INGRESOS_CURSOS',
       'Ingresos por cursos',
       'Ingresos facturados por periodo',
       NULL,
       (SELECT id_unidad FROM cat_unidad WHERE clave='mxn'),
       (SELECT id_frecuencia FROM cat_frecuencia WHERE clave='mensual'),
       (SELECT id_fuente FROM fuente_dato WHERE nombre='PASD'),
       0,
       1
ON DUPLICATE KEY UPDATE activo=VALUES(activo);

INSERT INTO indicador (id_area, id_jefatura, id_categoria, clave, nombre, descripcion, formula, id_unidad, id_frecuencia, id_fuente, requiere_carrera, activo)
SELECT (SELECT id_area FROM area WHERE nombre='CLE'),
       (SELECT j.id_jefatura FROM jefatura j JOIN area a ON a.id_area=j.id_area AND a.nombre='CLE' LIMIT 1),
       (SELECT id_categoria FROM categoria_indicador WHERE nombre='Productividad'),
       'INSCRIPCIONES_IDIOMAS',
       'Inscripciones a programas de idiomas',
       'Conteo de inscripciones',
       NULL,
       (SELECT id_unidad FROM cat_unidad WHERE clave='numero'),
       (SELECT id_frecuencia FROM cat_frecuencia WHERE clave='trimestral'),
       (SELECT id_fuente FROM fuente_dato WHERE nombre='Kardex'),
       0,
       1
ON DUPLICATE KEY UPDATE activo=VALUES(activo);

-- Asigna rol Admin al usuario admin
INSERT IGNORE INTO usuario_rol (id_usuario, id_rol)
SELECT u.id_usuario, r.id_rol
FROM usuario u, rol r
WHERE u.correo='admin@duacyd.mx' AND r.nombre='Administrador';

-- =================================
-- 11) ÍNDICES RECOMENDADOS
-- =================================
CREATE INDEX ix_indicador_area ON indicador(id_area);
CREATE INDEX ix_meta_periodo ON meta_indicador(id_periodo);
CREATE INDEX ix_valor_indicador ON valor_indicador(id_indicador);
CREATE INDEX ix_valor_carrera ON valor_indicador(id_carrera);

-- =================================
-- 12) EJEMPLOS DE CARGA (usa el SP)
-- =================================
-- Ejemplo: upsert matrícula SUAYED por carrera en 2025-1
-- (Ajusta IDs según tus seeds reales)
-- CALL sp_upsert_valor_indicador(p_id_indicador, p_id_periodo, p_id_carrera, p_valor, p_id_usuario, p_id_lote);

-- SELECT helper IDs:
-- SELECT id_periodo FROM periodo WHERE clave='2025-1';
-- SELECT id_indicador FROM indicador WHERE clave='MATRICULA_TOTAL' AND id_area=(SELECT id_area FROM area WHERE nombre='SUAYED');
-- SELECT id_carrera FROM carrera WHERE nombre='Derecho';

-- CALL sp_upsert_valor_indicador( <id_indicador_suayed_matricula>, <idp_2025_1>, <idc_derecho>, 1234, <id_admin>, NULL );
-- CALL sp_upsert_valor_indicador( <id_indicador_suayed_matricula>, <idp_2025_1>, <idc_ri>, 850, <id_admin>, NULL );
-- CALL sp_upsert_valor_indicador( <id_indicador_suayed_matricula>, <idp_2025_1>, <idc_economia>, 910, <id_admin>, NULL );

-- Ejemplo: indicador sin carrera (EDCO ingresos, agosto 2025)
-- SELECT id_periodo FROM periodo WHERE clave='2025-08';
-- SELECT id_indicador FROM indicador WHERE clave='INGRESOS_CURSOS';
-- CALL sp_upsert_valor_indicador( <id_ingresos>, <idp_2025_08>, NULL, 250000.00, <id_admin>, NULL );
