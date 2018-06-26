###############
### imports ###
###############

from fabric.api import cd, env, lcd, put, prompt, local, sudo, run
from fabric.contrib.files import exists


##############
### config ###
##############

project = 'flask_project'
_local_app_dir = lambda app: './%s' % app
local_config_dir = './config'

REMOTE_WWW_DIR = '/home/www'
REMOTE_GIT_DIR = '/home/git'
_remote_flask_dir = lambda app: '{}/{}'.format(REMOTE_WWW_DIR, app)
REMOTE_NGINX_DIR = '/etc/nginx/sites-available'
REMOTE_SUPERVISOR_DIR = '/etc/supervisor/conf.d'

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


def install_flask(app):
    """
    1. Create project directories
    2. Create and activate a virtualenv
    3. Copy Flask files to remote host
    """
    if exists(REMOTE_WWW_DIR) is False:
        sudo('mkdir ' + REMOTE_WWW_DIR)
        sudo('chown {u}:{u} {d}'.format(u=env.user, d=REMOTE_WWW_DIR))
    if exists(_remote_flask_dir(app)) is False:
        run('mkdir -p {}/{}'.format(_remote_flask_dir(app), app))
    with lcd(_local_app_dir(app)):
        with cd(_remote_flask_dir(app)):
            run('virtualenv venv3 -p python3')
            run('source venv3/bin/activate')
            run('pip install Flask==0.10.1')
        with cd(_remote_flask_dir(app)):
            put('*', './{}'.format(app), use_sudo=False)


def configure_nginx(app):
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
    if exists('/etc/nginx/sites-enabled/%s' % app) is False:
        sudo('touch /etc/nginx/sites-available/%s' % app)
        sudo(('ln -s /etc/nginx/sites-available/{p}' +
             ' /etc/nginx/sites-enabled/{p}').format(p=app))
    with lcd(local_config_dir):
        with cd(REMOTE_NGINX_DIR):
            put('./%s' % app, './', use_sudo=True)
    sudo('/etc/init.d/nginx restart')


def configure_supervisor(app):
    """
    1. Create new supervisor config file
    2. Copy local config to remote config
    3. Register new command
    """
    if exists('/etc/supervisor/conf.d/%s.conf' % app) is False:
        with lcd(local_config_dir):
            with cd(REMOTE_SUPERVISOR_DIR):
                put('./%s.conf' % app, './', use_sudo=True)
                sudo('supervisorctl reread')
                sudo('supervisorctl update')


def configure_git(app):
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
                with lcd(local_config_dir):
                    with cd('hooks'):
                        with open(local_config_dir + '/post-receive', 'w') as hook:
                            hook.write("""#!/bin/sh
GIT_WORK_TREE=/home/www/%s git checkout -f
""" % app)
                        put('./post-receive', './', use_sudo=False)
                        sudo('chmod +x post-receive')


def run_app(app):
    """ Run the app! """
    with cd(_remote_flask_dir(app)):
        sudo('supervisorctl start %s' % app)

def stop_app(app):
    """ Run the app! """
    with cd(_remote_flask_dir(app)):
        sudo('supervisorctl stop %s' % app)


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

def restart(app):
        sudo('supervisorctl restart %s' % app)


def rollback(app, repo='production'):
    """
    1. Quick rollback in case of error
    2. Restart gunicorn via supervisor
    """
    with lcd(_local_app_dir(app)):
        local('git revert master  --no-edit')
        local('git push %s master' % repo)
        sudo('supervisorctl restart %s' % app)


def status():
    """ Is our app live? """
    sudo('supervisorctl status')


def create(app):
    install_requirements()
    install_flask(app)
    configure_nginx(app)
    configure_supervisor(app)
    configure_git(app)

def clean(app):
    stop_app(app)
    sudo('rm -rf %s' % REMOTE_WWW_DIR)
    sudo('rm -rf %s' % REMOTE_GIT_DIR)
    sudo('rm -f /etc/supervisor/conf.d/%s.conf' % app)
    sudo('rm -f /etc/nginx/sites-available/%s' % app)
    sudo('rm -f /etc/nginx/sites-enabled/%s' % app)
