migrate:
	python3 manage.py makemigrations
	python3 manage.py migrate

runserver:
	python3 manage.py runserver

qcluster:
	python3 manage.py qcluster

check:
	python3 manage.py check

superuser:
	python3 manage.py createsuperuser

collectstatic:
	python3 manage.py collectstatic

test:
	python3 manage.py test

count_lines:
	python3 count_lines.py

heroku_log:
	heroku logs --tail --app c-lara

backup_db:
	cp db.sqlite3 db.sqlite3.bkp

restore_db:
	cp db.sqlite3.bkp db.sqlite3 
