def test-deploy:
	fab -H linode --prompt-for-sudo-password foo.vahtras.se --module flask_project --app app --port 9000
