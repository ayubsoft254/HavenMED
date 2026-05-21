PROJECT_NAME ?= havenmed
COMPOSE_FILE ?= docker-compose.prod.yml
COMPOSE = docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE)

.PHONY: init build up down restart logs ps pull migrate collectstatic createsuperuser shell status

init:
	mkdir -p /opt/havenmed/shared/data /opt/havenmed/shared/media /opt/havenmed/shared/staticfiles

build:
	$(COMPOSE) build --pull

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

pull:
	$(COMPOSE) pull

migrate:
	$(COMPOSE) run --rm app python manage.py migrate --noinput

collectstatic:
	$(COMPOSE) run --rm app python manage.py collectstatic --noinput

createsuperuser:
	$(COMPOSE) run --rm app python manage.py createsuperuser

shell:
	$(COMPOSE) exec app sh

status:
	$(COMPOSE) ps
