import pathlib
import pip
import subprocess


def shell(cmd):
    subprocess.run(cmd.split())


deploy_host = input("Deploy host:")
deploy_user = input("Deploy user:")
deploy_module = input("module:")
deploy_app = input("app:")
deploy_port = input("port:")
deploy_site = input("site:")

# environment variables
with open('.envrc', 'a') as envrc:
    envrc.write(f'export DEPLOY_HOST={deploy_host}\n')
    envrc.write(f'export DEPLOY_USER={deploy_user}\n')
    envrc.write(f'export FLASK_MODULE={deploy_module}\n')
    envrc.write(f'export APP={deploy_app}\n')
    envrc.write(f'export PORT={deploy_port}\n')
    envrc.write(f'export SITE={deploy_site}\n')
    envrc.write('export PYTHONPATH=flask-deploy\n')

shell('direnv allow')

# install
pip.main('install -r flask-deploy/requirements.txt'.split())

shell('ln -s flask-deploy/fabfile.py .')

original_makefile = ""
if pathlib.Path('Makefile').is_file():
    original_makefile = open('Makefile').read()

with open("Makefile", "w") as makefile:
    makefile.write("include flask-deploy/Makefile\n")
    makefile.write(original_makefile)
