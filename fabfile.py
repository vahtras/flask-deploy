###############
### imports ###
###############

import os
import subprocess
from invoke import task
from patchwork.files import exists

##############
### config ###
##############

REMOTE_ROOT = '/home/www'
REMOTE_NGINX_DIR = '/etc/nginx/sites-available'
REMOTE_SUPERVISOR_DIR = '/etc/supervisor/conf.d'
SERVER_IP ="127.0.0.1"

def remote_site_dir(site):
    return f'{REMOTE_ROOT}/sites/{site}'

def remote_git_dir(site):
    return f'{REMOTE_ROOT}/sites/{site}/git'

def remote_flask_dir(site):
    return f'{REMOTE_ROOT}/sites/{site}/src'

user = 'olav'

#############
### tasks ###
#############

@task
def hello(c):
    c.run('echo "Hello world!"')

###########
# install #
###########

@task
def create(c, site):
    """
    Install a deployment from scratch
    """
    install_requirements(c)
    configure_git(c, site)
    install_flask(c, site)
    push_remote(c, site)
    generate_site_nginx(c, site)
    configure_nginx(c, site)
    configure_supervisor(c, site)
    #start

@task
def install_requirements(c):
    """
    Install required packages.

    Python
    Gunicorn
    Supervisor
    Git
    """
    c.sudo('apt-get update')
    c.sudo('apt-get install -y python3')
    c.sudo('apt-get install -y python3-pip')
    c.sudo('apt-get install -y python3-virtualenv')
    c.sudo('apt-get install -y nginx')
    c.sudo('apt-get install -y gunicorn3')
    c.sudo('apt-get install -y supervisor')
    c.sudo('apt-get install -y git')

@task
def install_site_dir(c, site):
    c.run(f'mkdir -p {remote_site_dir(site)}')

@task
def install_venv(c, site):
    c.run(f"""\
virtualenv {remote_site_dir(site)}/venv3 -p python3
source {remote_site_dir(site)}/venv3/bin/activate
pip install Flask
"""
    )

#######
# git #
#######

@task
def configure_git(c, site):
    """
    1. Setup bare Git repo
    2. Create post-receive hook
    """

    remote = remote_git_dir(site)
    if exists(c, remote):
        print(remote)
    else:
        print("Creating: " + remote)
        c.run(f'git init --bare {remote}')
        c.run(
            'echo "#!/bin/sh\n' 
            f'GIT_WORK_TREE={remote_flask_dir(site)}'
            f' git checkout -f" > {remote}/hooks/post-receive' 
        )
        c.run(f'chmod +x {remote_git_dir(site)}/hooks/post-receive')

#########
# flask #
#########

@task
def install_flask(c, site):
    """
    Install Flask project

    1. Create project directories
    2. Create and activate a virtualenv
    3. Checkout from previously configured git repo
    """

    if exists(c, remote_flask_dir(site)):
        print(f'{remote_flask_dir(site)} exists')
    else:
        c.run(f'mkdir -p {remote_flask_dir(site)}')
        install_venv(c, site)
#        with c.cd(remote_site_dir(site)):
#            c.run('''virtualenv venv3 -p python3
#source venv3/bin/activate
#pip install Flask
#'''
##            )
#
#        with c.cd(remote_git_dir(site)):
#            c.run(f"GIT_WORK_TREE={remote_flask_dir(site)} git checkout -f")
@task
def install_root(c):
    """
    Install root install directory
    """
    if exists(c, REMOTE_ROOT):
        print(REMOTE_ROOT)
    else:
        c.sudo(f'mkdir -p {REMOTE_ROOT}')
        c.sudo(f'chown {user}:{user} {REMOTE_ROOT}')

#########
# nginx #
#########

@task
def configure_nginx(c, site):
    """
    Configure nginx 

    1. Remove default nginx config file
    2. Create new config file
    3. Setup new symbolic link
    4. Copy local config to remote config
    5. Restart nginx
    """
    c.sudo('/etc/init.d/nginx start')

    disable_nginx_default(c)

    enabled = f'/etc/nginx/sites-enabled/{site}'
    available = f'/etc/nginx/sites-available/{site}'

    if exists(c, enabled) is False:
        c.sudo(f'touch {available}')
        c.sudo(f'ln -s {available} {enabled}')

    scp(c, f'./sites/{site}{available}', available)
    c.sudo('/etc/init.d/nginx restart')
    

@task
def disable_nginx_default(c):
    if exists(c,'/etc/nginx/sites-enabled/default'):
        c.sudo('rm /etc/nginx/sites-enabled/default')

@task
def enable_link(c, site):
    enabled = f'/etc/nginx/sites-enabled/{site}'
    available = f'/etc/nginx/sites-available/{site}'
    c.sudo(f'touch {available}')
    c.sudo(f'ln -s {available} {enabled}')

@task
def scp(c, source, target):
    dir_, file_ = os.path.split(target)
    c.put(source, f'/tmp/{file_}')
    c.sudo(f'mv /tmp/{file_} {target}')
    
    

##############
# supervisor #
##############

@task
def configure_supervisor(c, site):
    """
    Configure supervisor for nginx

    1. Create new supervisor config file
    2. Copy local config to remote config
    3. Register new command
    """
            
    if exists(c,f'/etc/supervisor/conf.d/{site}.conf') is False:
        c.put(
            f'./sites/{site}/etc/supervisor/conf.d/{site}.conf',
            f'/tmp/{site}.conf'
        )
        c.sudo(f'mv /tmp/{site}.conf /etc/supervisor/conf.d/{site}.conf')
        c.sudo('supervisorctl reread')
        c.sudo('supervisorctl update')

    

@task
def run_app(c, site):
    """ Run the app! """
    c.sudo(f'supervisorctl start {site}')

@task
def stop_app(c, site):
    """ Stop the app! """
    c.sudo(f'supervisorctl stop {site}')

@task
def restart(c, site):
        stop_app(c, site)
        run_app(c, site)

@task
def status(c):
    """ Is our app live? """
    c.sudo('supervisorctl status')

@task
def deploy(c, app, repo='production'):
    """
    1. Copy new Flask files
    2. Restart gunicorn via supervisor
    """
    local('git add -A')
    commit_message = prompt("Commit message?")
    local('git commit -am "{0}"'.format(commit_message))
    local('git push %s master' % repo)
    sudo('supervisorctl restart %s' % app)



@task
def rollback(c, site):
    """
    1. Quick rollback in case of error
    2. Restart gunicorn via supervisor
    """
    c.local(f'git revert master --no-edit')
    c.local(f'git push {site} master')
    c.sudo(f'supervisorctl restart {site}')


@task
def clean(c, site):
    """
    Clear a configuration from server
    """
    stop_app(c, site)
    c.sudo(f'rm -rf {remote_site_dir(site)}')
    c.sudo(f'rm -f /etc/supervisor/conf.d/{site}.conf')
    c.sudo(f'rm -f /etc/nginx/sites-available/{site}')
    c.sudo(f'rm -f /etc/nginx/sites-enabled/{site}')

def self_signed_cert():
    local("openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 ")


@task
def install_certbot(c):
    """
    Install certbot for letsencrypt
    """
    c.sudo('apt-get update')
    c.sudo('apt-get install python-certbot-nginx')

@task 
def install_cert(c):
    """
    Generate and install letsencrypt cert
    """
    c.sudo('certbot --nginx')

@task
def generate_site_nginx(c, site):
    """
    Generate configuration files for nginx
    """
    from sites.template import NGINX
    #c.local(f'mkdir -p sites/{site}/etc/nginx/sites-available')
    try:
        os.makedirs(f'sites/{site}/etc/nginx/sites-available')
    except FileExistsError:
        pass
    with open(f'sites/{site}/etc/nginx/sites-available/{site}', 'w') as f:
        f.write(NGINX.format(server_name=site, root=REMOTE_ROOT))
        

@task
def generate_site_supervisor(c, site, module, app):
    """
    Generate configuration files for supervisor/gunicorn
    """
    from sites.template import SUPERVISOR

    try:
        os.makedirs(f'sites/{site}/etc/supervisor/conf.d')
    except FileExistsError:
        pass

    with open(f'sites/{site}/etc/supervisor/conf.d/{site}.conf', 'w') as f:
        f.write(SUPERVISOR.format(
            program=site,
            module=module,
            app=app,
            site=site,
            root=REMOTE_ROOT,
            user=user,
            )
        )

####

@task
def add_remote(c, site, test_site=None):
    """
    Define remote repo for site to track
    """
    if test_site is None:
        test_site = site
    subprocess.run(
        f'git remote add {site} {user}@{test_site}:{remote_git_dir(site)}',
        shell=True
        )

@task
def push_remote(c, site):
    """
    Push to  remote repo
    """
    subprocess.run(f'git push {site} master:master', shell=True)
