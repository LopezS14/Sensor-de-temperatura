-- Activar la extensión TimescaleDB si no está activada aún.
-- Esta extensión es necesaria para usar funciones y estructuras específicas para series temporales.
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Crear la tabla 'dht_data' solo si no existe ya.
-- Esta tabla almacenará las lecturas del sensor DHT con su tiempo, temperatura y humedad.
CREATE TABLE IF NOT EXISTS dht_data(
    -- Columna 'time' para la marca de tiempo con zona horaria.
    -- No puede ser nula porque es clave para los datos temporales.
    time TIMESTAMPTZ NOT NULL,

    -- Columna 'temperatura' para guardar la temperatura como número decimal de alta precisión.
    temperatura DOUBLE PRECISION NOT NULL,

    -- Columna 'humidity' para guardar la humedad relativa como número decimal de alta precisión.
    humidity DOUBLE PRECISION NOT NULL
);

-- Convertir la tabla 'dht_data' en una hypertable.
-- Una hypertable es la estructura que usa TimescaleDB para optimizar el almacenamiento y consulta de datos por tiempo.
-- El campo 'time' es la columna que TimescaleDB usará para segmentar y organizar los datos temporalmente.
-- El parámetro 'if_not_exists => TRUE' evita error si la hypertable ya existe.
SELECT create_hypertable('dht_data', 'time', if_not_exists => TRUE);
