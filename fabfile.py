###############
### imports ###
###############

import os
from invoke import task
from patchwork.files import exists

##############
### config ###
##############

REMOTE_WWW_DIR = '/home/www/sites'
REMOTE_GIT_DIR = '/home/git'
REMOTE_NGINX_DIR = '/etc/nginx/sites-available'
REMOTE_SUPERVISOR_DIR = '/etc/supervisor/conf.d'
SERVER_IP = 0

def remote_flask_dir(proj, staging=""):
    remote = '%s/%s' % (REMOTE_WWW_DIR, proj)
    if staging:
        remote += "-" + staging
    return remote

user = 'olav'

#############
### tasks ###
#############

@task
def hello(c):
    c.run('echo "Hello world!"')

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
def install_www(c):
    """
    Install root www directory

    Here: /home/www
    """
    if exists(c, REMOTE_WWW_DIR):
        print(REMOTE_WWW_DIR)
    else:
        c.sudo(f'mkdir -p {REMOTE_WWW_DIR}')
        c.sudo('chown {u}:{u} {d}'.format(u=user, d=REMOTE_WWW_DIR))

@task
def install_flask(c, proj="proj", staging=""):
    """
    Install Flask project

    1. Create project directories
    2. Create and activate a virtualenv
    3. Checkout from previously configured git repo
    """

    install_www(c)

    if exists(c, remote_flask_dir(proj, staging)):
        print(remote_flask_dir(proj, staging))
    else:
        c.run(f'mkdir -p {remote_flask_dir(proj, staging)}')
        with c.cd(remote_flask_dir(proj, staging)):
            c.run('''virtualenv venv3 -p python3
source venv3/bin/activate
pip install Flask
'''
            )
        url = f"{user}@{SERVER_IP}:{remote_flask_dir(proj, staging)}.git"
        repo = "production"
        if staging:
            repo = "staging"
        c.local(f'git remote get-url {repo} || git remote add {repo} {url}')
        c.local(f'git push {repo} master')
        with c.cd(remote_git_dir(proj, staging)):
            c.run(f"GIT_WORK_TREE={remote_flask_dir(proj, staging)} git checkout -f")

@task
def configure_nginx(c, site, proj, staging=""):
    """
    Configure nginx 

    1. Remove default nginx config file
    2. Create new config file
    3. Setup new symbolic link
    4. Copy local config to remote config
    5. Restart nginx
    """
    c.sudo('/etc/init.d/nginx start')
    if exists(c,'/etc/nginx/sites-enabled/default'):
        c.sudo('rm /etc/nginx/sites-enabled/default')

    enabled = '/etc/nginx/sites-enabled/%s' % conf_name(proj, staging)
    available = '/etc/nginx/sites-available/%s' % conf_name(proj, staging)
    if exists(c, enabled) is False:
        c.sudo('touch %s' % available)
        c.sudo('ln -s %s %s' % (available, enabled))

    with c.cd(REMOTE_NGINX_DIR):
        conffile = proj
        if staging:
            conffile = "-".join([proj, staging])
        c.put(f'./config/sites/{site}{available}', f'/tmp/{conffile}')
    c.sudo(f"mv /tmp/{conffile} {available}")
    c.sudo('/etc/init.d/nginx restart')

def conf_name(proj, staging=""):
    """Generate production/staging configuration names"""
    if staging:
        return "-".join((proj ,staging))
    else:
        return proj

@task
def configure_supervisor(c, site, proj, staging=""):
    """
    Configure supervisor for nginx

    1. Create new supervisor config file
    2. Copy local config to remote config
    3. Register new command
    """
            
    if exists(c,'/etc/supervisor/conf.d/%s.conf' % conf_name(proj, staging)) is False:
        conffile = "%s.conf" % proj
        if staging:
            conffile =  "-".join([proj, staging]) + ".conf"
        c.put(
            f'./config/sites/{site}/etc/supervisor/conf.d/{conffile}',
            f'/tmp/{conffile}'
        )
        c.sudo(f'mv /tmp/{conffile} /etc/supervisor/conf.d/{conffile}')
        c.sudo('supervisorctl reread')
        c.sudo('supervisorctl update')


@task
def configure_git(c, proj, staging=""):
    """
    1. Setup bare Git repo
    2. Create post-receive hook
    """
    if exists(c, REMOTE_GIT_DIR):
        print(REMOTE_GIT_DIR)
    else:
        print("Creating: " + REMOTE_GIT_DIR)
        c.sudo('mkdir ' + REMOTE_GIT_DIR)
        c.sudo('chown {u}:{u} {d}'.format(u=user, d=REMOTE_GIT_DIR))

    if exists(c, remote_git_dir(proj, staging)):
        print(remote_git_dir(proj, staging))
    else:
        print("Creating: " + remote_git_dir(proj, staging))
        c.run('git init --bare %s' % remote_git_dir(proj, staging))
        c.run(
            'echo "#!/bin/sh\n' +
            f'GIT_WORK_TREE={REMOTE_WWW_DIR}/%s git checkout -f" > %s/hooks/post-receive' 
            %  (conf_name(proj, staging), remote_git_dir(proj, staging))
        )
        c.run(f'chmod +x {remote_git_dir(proj, staging)}/hooks/post-receive')

def remote_git_dir(proj, staging=""):
    return os.path.join(REMOTE_GIT_DIR, conf_name(proj, staging)) + ".git"
    

@task
def run_app(c, proj, staging=""):
    """ Run the app! """
    c.sudo('supervisorctl start %s' % conf_name(proj, staging))

@task
def stop_app(c, proj, staging=""):
    """ Stop the app! """
    c.sudo('supervisorctl stop %s' % conf_name(proj, staging))


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
def restart(c, proj, staging=""):
        stop_app(c, proj, staging)
        run_app(c, proj, staging)


@task
def rollback(c, proj, staging=''):
    """
    1. Quick rollback in case of error
    2. Restart gunicorn via supervisor
    """
    repo = {"": "production"}
    if staging:
        repo[staging] = staging
    c.local('git revert master --no-edit')
    c.local('git push %s master' % repo[staging])
    c.sudo('supervisorctl restart %s' % conf_name(proj, staging))


@task
def status(c):
    """ Is our app live? """
    c.sudo('supervisorctl status')


@task
def create(c, proj, staging=""):
    """
    Install a deployment from scratch
    """
    install_requirements(c)
    configure_git(c, proj, staging)
    install_flask(c, proj, staging)
    configure_nginx(c, proj, staging)
    configure_supervisor(c, proj, staging)

@task
def clean(c, proj, staging=""):
    """
    Clear a configuration from server
    """
    proj_ = conf_name(proj, staging)
    stop_app(c, proj, staging)
    c.sudo('rm -rf %s/%s' % (REMOTE_WWW_DIR, proj_))
    c.sudo('rm -rf %s/%s' % (REMOTE_GIT_DIR, proj_))
    c.sudo('rm -f /etc/supervisor/conf.d/%s.conf' % proj_)
    c.sudo('rm -f /etc/nginx/sites-available/%s' % proj_)
    c.sudo('rm -f /etc/nginx/sites-enabled/%s' % proj_)
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
