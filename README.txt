sudo -u www-data pip install flask-migrate
flask --app FoxyApp db init
flask --app FoxyApp db migrate
flask --app FoxyApp db upgrade