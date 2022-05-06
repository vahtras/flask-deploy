local:
	FLASK_APP=flask_project flask run
deploy:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password $$SITE --module flask_project --app app --port $$PORT

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
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password configure-nginx foo.bar

generate-site-supervisor:
	fab generate-site-supervisor $$SITE --module $$FLASK_APP --app $$APP --port $$PORT --deploy-user $$DEPLOYUSER
	@tree --noreport sites/$$SITE/etc/supervisor
	@cat sites/$$SITE/etc/supervisor/conf.d/$$SITE.conf | sed "s/^/        /"

configure-supervisor:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password configure-supervisor foo.bar

start-app:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password start-app foo.bar

install-cert:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password install-cert foo.bar
