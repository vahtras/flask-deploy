local:
	FLASK_APP=flask_project flask run
deploy:
	fab --hosts $$DEPLOYHOST --prompt-for-sudo-password $$SITE --module flask_project --app app --port 9000

configure-git:
	fab --hosts $$DEPLOYHOST configure-git $$SITE

install-flask-work-tree:
	fab --hosts $$DEPLOYHOST install-flask-work-tree $$SITE
