default:
	@echo "Local commands"
	@echo "──────────────"
	@echo "local:$$(python -c 'import fabfile; print(fabfile.local.__doc__)')"
	@echo "Remote commands"
	@echo "──────────────"
	@echo "add-remote:	$$(python -c 'import fabfile; print(fabfile.add_remote.__doc__)')"
	@echo "clean:	$$(python -c 'import fabfile; print(fabfile.clean.__doc__)')"
	@echo "configure-git:	$$(python -c 'import fabfile; print(fabfile.configure_git.__doc__)')"
	@echo "create:	$$(python -c 'import fabfile; print(fabfile.create.__doc__)')"
	@echo "generate-site-nginx:	$$(python -c 'import fabfile; print(fabfile.generate_site_nginx.__doc__)')"
	@echo "install-cert:	$$(python -c 'import fabfile; print(fabfile.install_cert.__doc__)')"
	@echo "install-flask-work-tree:	$$(python -c 'import fabfile; print(fabfile.install_flask_work_tree.__doc__)')"
	@echo "install-venv:	$$(python -c 'import fabfile; print(fabfile.install_venv.__doc__)')"
	@echo "list-ports:	$$(python -c 'import fabfile; print(fabfile.list_ports.__doc__)')"
	@echo "push-remote:	$$(python -c 'import fabfile; print(fabfile.push_remote.__doc__)')"
	@echo "start-app:	$$(python -c 'import fabfile; print(fabfile.start_app.__doc__)')"
	@echo "stop-app:	$$(python -c 'import fabfile; print(fabfile.stop_app.__doc__)')"
	@echo "restart-app:	$$(python -c 'import fabfile; print(fabfile.restart_app.__doc__)')"
	@echo "restart-all:	$$(python -c 'import fabfile; print(fabfile.restart_all.__doc__)')"
	@echo "status:	$$(python -c 'import fabfile; print(fabfile.status.__doc__)')"

local:
	FLASK_APP=$$FLASK_MODULE flask run
create:
	fab --hosts $$DEPLOY_HOST --prompt-for-sudo-password create $$SITE --module $$FLASK_MODULE --app $$APP --port $$PORT

configure-git:
	fab --hosts $$DEPLOY_HOST configure-git $$SITE

install-flask-work-tree:
	fab --hosts $$DEPLOY_HOST install-flask-work-tree $$SITE

install-venv:
	fab --hosts $$DEPLOY_HOST install-venv $$SITE

add-remote:
	fab add-remote $$SITE --deploy-user $$DEPLOY_USER --deploy-host $$DEPLOY_HOST

push-remote:
	fab push-remote $$SITE

generate-site-nginx:
	fab generate-site-nginx $$SITE --port $$PORT
	@tree --noreport sites/$$SITE/etc/nginx
	@cat sites/$$SITE/etc/nginx/sites-available/$$SITE | sed "s/^/        /"

configure-nginx:
	fab --hosts $$DEPLOY_HOST --prompt-for-sudo-password configure-nginx $$SITE

generate-site-supervisor:
	fab generate-site-supervisor $$SITE --module $$FLASK_MODULE --app $$APP --port $$PORT --deploy-user $$DEPLOY_USER
	@tree --noreport sites/$$SITE/etc/supervisor
	@cat sites/$$SITE/etc/supervisor/conf.d/$$SITE.conf | sed "s/^/        /"

configure-supervisor:
	fab --hosts $$DEPLOY_HOST --prompt-for-sudo-password configure-supervisor $$SITE

start-app:
	fab --hosts $$DEPLOY_HOST --prompt-for-sudo-password start-app $$SITE

stop-app:
	fab --hosts $$DEPLOY_HOST --prompt-for-sudo-password stop-app $$SITE

restart-app:
	fab --hosts $$DEPLOY_HOST --prompt-for-sudo-password restart-app $$SITE

install-cert:
	fab --hosts $$DEPLOY_HOST --prompt-for-sudo-password install-cert $$SITE

clean:
	fab --hosts $$DEPLOY_HOST --prompt-for-sudo-password clean $$SITE

status:
	fab --hosts $$DEPLOY_HOST --prompt-for-sudo-password status

list-ports:
	fab --hosts $$DEPLOY_HOST --prompt-for-sudo-password list-ports
