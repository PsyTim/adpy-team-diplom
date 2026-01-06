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
    code_verifier VARCHAR(64), --Код верификации
    device_id VARCHAR(86),
    access_token VARCHAR(262),
    refresh_token VARCHAR(241),
    state SMALLINT,
    to_del VARCHAR(50) NOT NULL DEFAULT '',
    state_history VARCHAR(1000),
    last_visit TIMESTAMP NOT NULL DEFAULT NOW(),
    filter_age_from SMALLINT NULL,
    filter_age_to SMALLINT NULL,
    filter_gender SMALLINT NULL,
    filter_city_id INTEGER NULL,
    filter_city VARCHAR(180) NULL
);

DROP TABLE IF EXISTS profiles CASCADE;
CREATE TABLE profiles (
    id SERIAL PRIMARY KEY,
    vk_id BIGINT NOT NULL UNIQUE,
    domain VARCHAR(32),
    gender SMALLINT NULL,
    birthday DATE NULL,
    city_id INTEGER NULL,
    city VARCHAR(180) NULL
);

DROP TABLE IF EXISTS users_profiles CASCADE;
CREATE TABLE users_profiles (
    id SERIAL UNIQUE,
    user_id INTEGER REFERENCES users(id),
    profile_id INTEGER REFERENCES profiles(id),
    viewed TIMESTAMP,
    favorit TIMESTAMP,
    blacklisted TIMESTAMP,
	CONSTRAINT pk PRIMARY KEY (user_id, profile_id)
);

