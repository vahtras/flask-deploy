###############
### imports ###
###############

import os
from fabric.api import cd, env, lcd, put, prompt, local, sudo, run
from fabric.contrib.files import exists


##############
### config ###
##############

project = 'flask_project'
_local_app_dir = lambda app: './%s' % app
def local_config_dir(proj, staging):
    if staging:
        return './config/staging'
    else:
        return './config/production'

REMOTE_WWW_DIR = '/home/www'
REMOTE_GIT_DIR = '/home/git'
REMOTE_NGINX_DIR = '/etc/nginx/sites-available'
REMOTE_SUPERVISOR_DIR = '/etc/supervisor/conf.d'

def remote_flask_dir(proj, staging=""):
    remote = '%s/%s' % (REMOTE_WWW_DIR, proj)
    if staging:
        remote += "-" + staging
    return remote


env.hosts = ['104.200.30.58']  # replace with IP address or hostname
env.user = 'olav'
# env.password = 'blah!'


#############
### tasks ###
#############

def install_requirements():
    """ Install required packages. """
    sudo('apt-get update')
    sudo('apt-get install -y python3')
    sudo('apt-get install -y python3-pip')
    sudo('apt-get install -y python3-virtualenv')
    sudo('apt-get install -y nginx')
    sudo('apt-get install -y gunicorn3')
    sudo('apt-get install -y supervisor')
    sudo('apt-get install -y git')


def install_www():
    if exists(REMOTE_WWW_DIR) is False:
        sudo('mkdir ' + REMOTE_WWW_DIR)
        sudo('chown {u}:{u} {d}'.format(u=env.user, d=REMOTE_WWW_DIR))

def install_flask(proj, staging=""):
    """
    1. Create project directories
    2. Create and activate a virtualenv
    3. Copy Flask files to remote host
    """

    install_www()

    if exists(remote_flask_dir(proj, staging)) is False:
        run('mkdir -p {}/{}'.format(remote_flask_dir(proj, staging), proj))
    with lcd(_local_app_dir(proj)):
        with cd(remote_flask_dir(proj, staging)):
            run('virtualenv venv3 -p python3')
            run('source venv3/bin/activate')
            run('pip install Flask==0.10.1')
        with cd(remote_flask_dir(proj, staging)):
            put('*', './{}'.format(proj), use_sudo=False)


def configure_nginx(proj, staging=""):
    """
    1. Remove default nginx config file
    2. Create new config file
    3. Setup new symbolic link
    4. Copy local config to remote config
    5. Restart nginx
    """
    sudo('/etc/init.d/nginx start')
    if exists('/etc/nginx/sites-enabled/default'):
        sudo('rm /etc/nginx/sites-enabled/default')

    enabled = '/etc/nginx/sites-enabled/%s' % proj
    available = '/etc/nginx/sites-available/%s' % proj
    if exists(enabled) is False:
        sudo('touch %s' % available)
        sudo('ln -s %s %s' % (avaliable, enabled))

    config = local_config_dir(proj, staging)

    with lcd(config):
        with cd(REMOTE_NGINX_DIR):
            conffile = proj
            if staging:
                conffile = "-".join([proj, staging])
            put(conffile, './', use_sudo=True)
    sudo('/etc/init.d/nginx restart')

def conf_name(proj, staging=""):
    if staging:
        return "-".join((proj ,staging))
    else:
        return proj

def configure_supervisor(proj, staging=""):
    """
    1. Create new supervisor config file
    2. Copy local config to remote config
    3. Register new command
    """
            
    if exists('/etc/supervisor/conf.d/%s.conf' % proj) is False:
        with lcd(local_config_dir(proj, staging)):
            with cd(REMOTE_SUPERVISOR_DIR):
                conffile = "%s.conf" % proj
                if staging:
                    conffile =  "-".join([proj, staging]) + ".conf"
                put(conffile,  './', use_sudo=True)
                sudo('supervisorctl reread && supervisorctl update')


def configure_git(app, staging=""):
    """
    1. Setup bare Git repo
    2. Create post-receive hook
    """
    if exists(REMOTE_GIT_DIR) is False:
        sudo('mkdir ' + REMOTE_GIT_DIR)
        sudo('chown {u}:{u} {d}'.format(u=env.user, d=REMOTE_GIT_DIR))
        with cd(REMOTE_GIT_DIR):
            run('mkdir %s.git' % app)
            with cd('%s.git' % app):
                run('git init --bare')
                with lcd(local_config_dir(app, staging)):
                    with cd('hooks'):
                        with open(local_config_dir(app, staging) + '/post-receive', 'w') as hook:
                            hook.write("""#!/bin/sh
GIT_WORK_TREE=/home/www/%s git checkout -f
""" % conf_name(app, staging))
                        put('./post-receive', './', use_sudo=False)
                        sudo('chmod +x post-receive')


def run_app(proj, staging=""):
    """ Run the app! """
    with cd(remote_flask_dir(proj, staging)):
        sudo('supervisorctl start %s' % conf_name(proj, staging))

def stop_app(proj, staging=""):
    """ Stop the app! """
    with cd(remote_flask_dir(proj, staging)):
        sudo('supervisorctl stop %s' % conf_name(proj, staging))


def deploy(app, repo='production'):
    """
    1. Copy new Flask files
    2. Restart gunicorn via supervisor
    """
    with lcd(_local_app_dir(app)):
        local('git add -A')
        commit_message = prompt("Commit message?")
        local('git commit -am "{0}"'.format(commit_message))
        local('git push %s master' % repo)
        sudo('supervisorctl restart %s' % app)

def restart(proj, staging=""):
        stop_app(proj, staging)
        run_app(proj, staging)


def rollback(proj, staging=''):
    """
    1. Quick rollback in case of error
    2. Restart gunicorn via supervisor
    """
    repo = {"": "production"}
    if staging:
        repo[staging] = staging
    with lcd(_local_app_dir(proj)):
        local('git revert master --no-edit')
        local('git push %s master' % repo[staging])
        sudo('supervisorctl restart %s' % conf_name(proj, staging))


def status():
    """ Is our app live? """
    sudo('supervisorctl status')


def create(proj, staging=""):
    install_requirements()
    install_flask(proj, staging)
    configure_nginx(proj, staging)
    configure_supervisor(proj, staging)
    configure_git(proj, staging)

def clean(app):
    stop_app(app)
    sudo('rm -rf %s' % REMOTE_WWW_DIR)
    sudo('rm -rf %s' % REMOTE_GIT_DIR)
    sudo('rm -f /etc/supervisor/conf.d/%s.conf' % app)
    sudo('rm -f /etc/nginx/sites-available/%s' % app)
    sudo('rm -f /etc/nginx/sites-enabled/%s' % app)
