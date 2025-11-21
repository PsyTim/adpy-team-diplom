DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    vk_id BIGINT NOT NULL,
    gender SMALLINT NULL,
    birthday DATE NULL,
    city_id INTEGER NULL,
    city VARCHAR(180) NULL,
    -- согласно Книге рекордов Гиннесса, самое длинное наименование населённого пункта 
    -- в мире — у столицы Таиланда Бангкока, полное название которого включает 168 букв
    last_visit TIMESTAMP NOT NULL,
    filter_age_from SMALLINT NULL,
    filter_age_to SMALLINT NULL,
    filter_gender SMALLINT NULL,
    filter_city_id INTEGER NULL,
    filter_city VARCHAR(180) NULL
);