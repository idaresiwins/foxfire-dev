sudo -u www-data pip install flask-migrate
flask --app FoxyApp db init
flask --app FoxyApp db migrate
flask --app FoxyApp db upgrade



ALTER TABLE product ADD COLUMN veg_sale_bool boolean DEFAULT TRUE;

UPDATE product
SET veg_sale_bool = CASE
    WHEN LOWER(veg_sale) IN ('true', 'yes', '1') THEN TRUE
    ELSE FALSE
END;
ALTER TABLE product DROP COLUMN veg_sale;
ALTER TABLE product RENAME COLUMN veg_sale_bool TO veg_sale;

