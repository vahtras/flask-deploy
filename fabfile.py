###############
### imports ###
###############

import os
#from fabric.api import cd, env, lcd, put, prompt, local, sudo, run
#from fabric.contrib.files import exists
from fabric import Connection
c = Connection('104.200.30.58')


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


# env.hosts = ['104.200.30.58']  # replace with IP address or hostname
user = 'olav'
# env.password = 'blah!'



#############
### tasks ###
#############

def install_requirements():
    """ Install required packages. """
    c.sudo('apt-get update')
    c.sudo('apt-get install -y python3')
    c.sudo('apt-get install -y python3-pip')
    c.sudo('apt-get install -y python3-virtualenv')
    c.sudo('apt-get install -y nginx')
    c.sudo('apt-get install -y gunicorn3')
    c.sudo('apt-get install -y supervisor')
    c.sudo('apt-get install -y git')


def install_www():
    if c.exists(REMOTE_WWW_DIR) is False:
        c.sudo('mkdir ' + REMOTE_WWW_DIR)
        c.sudo('chown {u}:{u} {d}'.format(u=user, d=REMOTE_WWW_DIR))

def install_flask(proj, staging=""):
    """
    1. Create project directories
    2. Create and activate a virtualenv
    3. Copy Flask files to remote host
    """

    install_www()

    if c.exists(remote_flask_dir(proj, staging)) is False:
        c.run('mkdir -p {}/{}'.format(remote_flask_dir(proj, staging), proj))
    with c.lcd(_local_app_dir(proj)):
        with c.cd(remote_flask_dir(proj, staging)):
            c.run('virtualenv venv3 -p python3')
            c.run('source venv3/bin/activate')
            c.run('pip install Flask==0.10.1')
        with c.cd(remote_flask_dir(proj, staging)):
            c.put('*', './{}'.format(proj), use_sudo=False)


def configure_nginx(proj, staging=""):
    """
    1. Remove default nginx config file
    2. Create new config file
    3. Setup new symbolic link
    4. Copy local config to remote config
    5. Restart nginx
    """
    c.sudo('/etc/init.d/nginx start')
    if c.exists('/etc/nginx/sites-enabled/default'):
        c.sudo('rm /etc/nginx/sites-enabled/default')

    enabled = '/etc/nginx/sites-enabled/%s' % conf_name(proj, staging)
    available = '/etc/nginx/sites-available/%s' % conf_name(proj, staging)
    if c.exists(enabled) is False:
        c.sudo('touch %s' % available)
        c.sudo('ln -s %s %s' % (available, enabled))

    config = local_config_dir(proj, staging)

    with c.lcd(config):
        with c.cd(REMOTE_NGINX_DIR):
            conffile = proj
            if staging:
                conffile = "-".join([proj, staging])
            c.put(conffile, './', use_sudo=True)
    c.sudo('/etc/init.d/nginx restart')

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
            
    if c.exists('/etc/supervisor/conf.d/%s.conf' % conf_name(proj, staging)) is False:
        with c.lcd(local_config_dir(proj, staging)):
            with c.cd(REMOTE_SUPERVISOR_DIR):
                conffile = "%s.conf" % proj
                if staging:
                    conffile =  "-".join([proj, staging]) + ".conf"
                c.put(conffile,  './', use_sudo=True)
                c.sudo('supervisorctl reread && supervisorctl update')


def configure_git(proj, staging=""):
    """
    1. Setup bare Git repo
    2. Create post-receive hook
    """
    if c.exists(REMOTE_GIT_DIR) is False:
        c.sudo('mkdir ' + REMOTE_GIT_DIR)
        c.sudo('chown {u}:{u} {d}'.format(u=user, d=REMOTE_GIT_DIR))
    if c.exists(REMOTE_GIT_DIR + '/%s' % conf_name(proj, staging)) is False:
        with c.cd(REMOTE_GIT_DIR):
            c.run('mkdir %s.git' % conf_name(proj, staging))
            with c.cd('%s.git' % conf_name(proj, staging)):
                c.run('git init --bare')
                with c.lcd(local_config_dir(proj, staging)):
                    with c.cd('hooks'):
                        with open(local_config_dir(proj, staging) + '/post-receive', 'w') as hook:
                            hook.write("""#!/bin/sh
GIT_WORK_TREE=/home/www/%s git checkout -f
""" % conf_name(proj, staging))
                        c.put('./post-receive', './', use_sudo=False)
                        c.sudo('chmod +x post-receive')


def run_app(proj, staging=""):
    """ Run the app! """
    with c.cd(remote_flask_dir(proj, staging)):
        c.sudo('supervisorctl start %s' % conf_name(proj, staging))

def stop_app(proj, staging=""):
    """ Stop the app! """
    with c.cd(remote_flask_dir(proj, staging)):
        c.sudo('supervisorctl stop %s' % conf_name(proj, staging))


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
    with c.lcd(_local_app_dir(proj)):
        c.local('git revert master --no-edit')
        c.local('git push %s master' % repo[staging])
        c.sudo('supervisorctl restart %s' % conf_name(proj, staging))


def status():
    """ Is our app live? """
    c.sudo('supervisorctl status')


def create(proj, staging=""):
    install_requirements()
    install_flask(proj, staging)
    configure_nginx(proj, staging)
    configure_supervisor(proj, staging)
    configure_git(proj, staging)

def clean(proj, staging=""):
    proj_ = conf_name(proj, staging)
    stop_app(proj_)
    c.sudo('rm -rf %s/%s' % (REMOTE_WWW_DIR, proj_))
    c.sudo('rm -rf %s/%s' % (REMOTE_GIT_DIR, proj_))
    c.sudo('rm -f /etc/supervisor/conf.d/%s.conf' % proj_)
    c.sudo('rm -f /etc/nginx/sites-available/%s' % proj_)
    c.sudo('rm -f /etc/nginx/sites-enabled/%s' % proj_)
