CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE users (
    "id" SERIAL NOT NULL,
    "uu" UUID NOT NULL UNIQUE,
    "discord_id" BIGINT NOT NULL UNIQUE,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "premium" BOOLEAN NOT NULL,
    "contributor" BOOLEAN NOT NULL,
    "moderator" BOOLEAN NOT NULL,
    "referral" VARCHAR(32) UNIQUE NOT NULL,
    PRIMARY KEY ("uu")
);

CREATE TABLE portfolios (
    "uu" UUID NOT NULL,
    "symbol" VARCHAR(64) NOT NULL,
    "quantity" double precision NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("uu", "symbol")
);

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON portfolios
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

CREATE TABLE transactions (
    "id" BIGSERIAL NOT NULL,
    "symbol" VARCHAR(64) NOT NULL,
    "quantity" double precision NOT NULL,
    "price" double precision NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user" UUID NOT NULL
);


CREATE TABLE referrals (
    "user" UUID NOT NULL,
    "referred_by"  VARCHAR(32) NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY ("user")
);

CREATE TABLE balance (
    "user" UUID NOT NULL,
    "balance" double precision NOT NULL,
    "updated_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY("user")
);

CREATE TRIGGER set_timestamp
BEFORE UPDATE ON balance
FOR EACH ROW
EXECUTE PROCEDURE trigger_set_timestamp();

CREATE table daily_reminder (
    "discord_id" BIGINT NOT NULL,
    "remind" BOOLEAN NOT NULL,
    PRIMARY KEY ("discord_id")
);

