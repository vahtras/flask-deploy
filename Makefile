local:
	FLASK_APP=$$FLASK_MODULE flask run
create:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password create $$SITE --module $$FLASK_MODULE --app $$APP --port $$PORT

configure-git:
	fab --hosts $$DEPLOYHOST configure-git $$SITE

install-flask-work-tree:
	fab --hosts $$DEPLOYHOST install-flask-work-tree $$SITE

install-venv:
	fab --hosts $$DEPLOYHOST install-venv $$SITE

add-remote:
	fab add-remote $$SITE --deploy-user $$DEPLOYUSER --deploy-host $$DEPLOYHOST

push-remote:
	fab push-remote $$SITE

generate-site-nginx:
	fab generate-site-nginx $$SITE --port $$PORT
	@tree --noreport sites/$$SITE/etc/nginx
	@cat sites/$$SITE/etc/nginx/sites-available/$$SITE | sed "s/^/        /"

configure-nginx:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password configure-nginx $$SITE

generate-site-supervisor:
	fab generate-site-supervisor $$SITE --module $$FLASK_MODULE --app $$APP --port $$PORT --deploy-user $$DEPLOYUSER
	@tree --noreport sites/$$SITE/etc/supervisor
	@cat sites/$$SITE/etc/supervisor/conf.d/$$SITE.conf | sed "s/^/        /"

configure-supervisor:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password configure-supervisor $$SITE

start-app:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password start-app $$SITE

restart-app:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password restart-app $$SITE

install-cert:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password install-cert $$SITE

clean:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password clean $$SITE
