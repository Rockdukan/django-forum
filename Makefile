clean:	## Очистить .pyc-файлы и __pycache__
	find . -name "*.pyc" -delete
	find . -depth -name "__pycache__" -type d -exec rm -rf {} +

install:	## Синхронизировать зависимости (uv)
	uv sync

collectstatic:	## Собрать статические файлы (production)
	uv run manage.py collectstatic --settings=core.settings.production

createsuperuser:	## Создать суперпользователя (development)
	uv run manage.py createsuperuser --settings=core.settings.development

createsuperuser-prod:	## Создать суперпользователя (production)
	uv run manage.py createsuperuser --settings=core.settings.production

fixtures:	## Загрузить демо-данные форума (fixtures/forum_demo.json)
	uv run manage.py loaddata fixtures/forum_demo.json --settings=core.settings.development

fixtures-prod:	## Загрузить демо-данные форума (production)
	uv run manage.py loaddata fixtures/forum_demo.json --settings=core.settings.production

help:	## Показать список доступных команд
	@echo ""
	@echo "Доступные команды:"
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*##/ {printf " \033[36m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""

migrate:	## makemigrations + migrate (core.settings.development)
	uv run manage.py makemigrations --settings=core.settings.development
	uv run manage.py migrate --settings=core.settings.development

migrate-prod:	## makemigrations + migrate (core.settings.production)
	uv run manage.py makemigrations --settings=core.settings.production
	uv run manage.py migrate --settings=core.settings.production

run:	## Запустить сервер (development)
	uv run python manage.py runserver --settings=core.settings.development

run-prod:	## Запустить сервер (production)
	uv run manage.py runserver --settings=core.settings.production

shell:	## Django shell (development)
	uv run manage.py shell --settings=core.settings.development

shell-prod:	## Django shell (production)
	uv run manage.py shell --settings=core.settings.production

test:	## Тесты: forum и site_pages (development)
	uv run manage.py test apps.forum.tests apps.site_pages.tests --settings=core.settings.development

test-prod:	## Тесты: forum и site_pages (core.settings.production)
	uv run manage.py test apps.forum.tests apps.site_pages.tests --settings=core.settings.production

to-req:	## requirements.txt из pyproject.toml (нужен пакет toml)
	python3 -c "import tomllib, pathlib; d = tomllib.loads(pathlib.Path('pyproject.toml').read_text()); print('\n'.join(d['project']['dependencies']))" > requirements.txt

.PHONY: clean install collectstatic createsuperuser createsuperuser-prod fixtures fixtures-prod help migrate migrate-prod run run-prod shell shell-prod test test-prod to-req
