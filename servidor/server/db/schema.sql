-- Esquema de la base de datos de ClasifIoT (MySQL 8).
-- Uso:  mysql -u root -p < server/db/schema.sql

CREATE DATABASE IF NOT EXISTS clasifiot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE clasifiot;

-- Un lote va desde un "start" hasta un "stop" (o una emergencia).
CREATE TABLE IF NOT EXISTS batches (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    started_at  DATETIME(3) NOT NULL,
    ended_at    DATETIME(3) NULL,
    product     VARCHAR(50) NOT NULL DEFAULT 'manzana'
);

-- Una fila por manzana. Se crea al llegar a la cámara (arrival), se completa
-- con la clasificación (result) y con el desvío (diverted).
CREATE TABLE IF NOT EXISTS pieces (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    batch_id        INT NULL,
    piece_id        INT NOT NULL,              -- número que asigna el Arduino
    ts              DATETIME(3) NOT NULL,      -- llegada a la cámara
    color           VARCHAR(20) NULL,
    is_defective    BOOLEAN NULL,
    confidence      FLOAT NULL,
    output_channel  TINYINT NULL,              -- salida real (la que informa el Arduino)
    image_path      VARCHAR(255) NULL,         -- ruta relativa, no la imagen
    diverted_ts     DATETIME(3) NULL,
    true_color      VARCHAR(20) NULL,          -- se anota a mano en las pruebas
    true_defective  BOOLEAN NULL,              -- se anota a mano en las pruebas
    CONSTRAINT fk_pieces_batch FOREIGN KEY (batch_id) REFERENCES batches(id),
    INDEX idx_batch_piece (batch_id, piece_id)
);

-- Eventos del supervisor con LLM (fuera del MVP; la tabla queda lista).
CREATE TABLE IF NOT EXISTS supervision_events (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    ts              DATETIME(3) NOT NULL,
    status          VARCHAR(30) NOT NULL,
    description     TEXT NULL,
    recommend_stop  BOOLEAN NOT NULL DEFAULT FALSE,
    image_path      VARCHAR(255) NULL
);

-- Configuración editable desde el dashboard.
CREATE TABLE IF NOT EXISTS settings (
    `key`   VARCHAR(50) PRIMARY KEY,
    `value` VARCHAR(255) NOT NULL
);

-- Valores por defecto (no pisa los que ya existan).
INSERT IGNORE INTO settings (`key`, `value`) VALUES
    ('grupo_a_colores', 'rojo'),     -- colores que van a la salida 2 (separados por coma)
    ('umbral_confianza', '0.6'),     -- bajo este valor la manzana va a la salida 3
    ('velocidad_mm_s', '30');        -- velocidad de la banda (28BYJ-48: máximo 40)
