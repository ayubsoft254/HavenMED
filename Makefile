PROJECT_NAME ?= havenmed
COMPOSE_FILE ?= docker-compose.prod.yml
COMPOSE = docker compose -p $(PROJECT_NAME) -f $(COMPOSE_FILE)
APP_UID ?= 1001
APP_GID ?= 1001
DATA_DIR ?= /opt/havenmed/shared/data
MEDIA_DIR ?= /opt/havenmed/shared/media
STATIC_DIR ?= /opt/havenmed/shared/staticfiles

.PHONY: init fix-perms build up down restart logs ps pull migrate collectstatic createsuperuser shell status

init:
	mkdir -p $(DATA_DIR) $(MEDIA_DIR) $(STATIC_DIR)
	chown -R $(APP_UID):$(APP_GID) $(DATA_DIR) $(MEDIA_DIR) $(STATIC_DIR)
	chmod -R u+rwX,g+rwX $(DATA_DIR) $(MEDIA_DIR) $(STATIC_DIR)

fix-perms:
	chown -R $(APP_UID):$(APP_GID) $(DATA_DIR) $(MEDIA_DIR) $(STATIC_DIR)
	chmod -R u+rwX,g+rwX $(DATA_DIR) $(MEDIA_DIR) $(STATIC_DIR)

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
