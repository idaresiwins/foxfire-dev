sudo -u www-data pip install flask-migrate

flask --app FoxyApp db init
flask --app FoxyApp db migrate
flask --app FoxyApp db upgrade

alter table product add column archive boolean not null default False;
alter table user add column archive boolean not null default False;

ALTER TABLE product ADD COLUMN veg_sale_bool boolean DEFAULT TRUE;
UPDATE product
SET veg_sale_bool = CASE
    WHEN LOWER(veg_sale) IN ('true', 'yes', '1') THEN TRUE
    ELSE FALSE
END;
ALTER TABLE product DROP COLUMN veg_sale;
ALTER TABLE product RENAME COLUMN veg_sale_bool TO veg_sale;

ALTER TABLE user ADD COLUMN prepaid_bool boolean DEFAULT TRUE;
UPDATE user
SET prepaid_bool = CASE
    WHEN LOWER(prepaid) IN ('true', 'yes', '1') THEN TRUE
    ELSE FALSE
END;
ALTER TABLE user DROP COLUMN prepaid;
ALTER TABLE user RENAME COLUMN prepaid_bool TO prepaid;

ALTER TABLE toggle ADD COLUMN set_toggle_bool boolean DEFAULT TRUE;
UPDATE toggle
SET set_toggle_bool = CASE
    WHEN LOWER(set_toggle) IN ('true', 'yes', '1') THEN TRUE
    ELSE FALSE
END;
ALTER TABLE toggle DROP COLUMN set_toggle;
ALTER TABLE toggle RENAME COLUMN set_toggle_bool TO set_toggle;
