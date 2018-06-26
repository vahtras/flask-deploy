###############
### imports ###
###############

from fabric.api import cd, env, lcd, put, prompt, local, sudo, run
from fabric.contrib.files import exists


##############
### config ###
##############

project = 'flask_project'
local_app_dir = './{}'.format(project)
local_config_dir = './config'

remote_app_dir = '/home/www'
remote_git_dir = '/home/git'
remote_flask_dir = '{}/{}'.format(remote_app_dir, project)
remote_nginx_dir = '/etc/nginx/sites-available'
remote_supervisor_dir = '/etc/supervisor/conf.d'

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


def install_flask():
    """
    1. Create project directories
    2. Create and activate a virtualenv
    3. Copy Flask files to remote host
    """
    if exists(remote_app_dir) is False:
        sudo('mkdir ' + remote_app_dir)
        sudo('chown {u}:{u} {d}'.format(u=env.user, d=remote_app_dir))
    if exists(remote_flask_dir) is False:
        run('mkdir -p {}/{}'.format(remote_flask_dir, project))
    with lcd(local_app_dir):
        with cd(remote_flask_dir):
            run('virtualenv venv3 -p python3')
            run('source venv3/bin/activate')
            run('pip install Flask==0.10.1')
        with cd(remote_flask_dir):
            put('*', './{}'.format(project), use_sudo=False)


def configure_nginx():
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
    if exists('/etc/nginx/sites-enabled/%s' % project) is False:
        sudo('touch /etc/nginx/sites-available/%s' % project)
        sudo(('ln -s /etc/nginx/sites-available/{p}' +
             ' /etc/nginx/sites-enabled/{p}').format(p=project))
    with lcd(local_config_dir):
        with cd(remote_nginx_dir):
            put('./%s' % project, './', use_sudo=True)
    sudo('/etc/init.d/nginx restart')


def configure_supervisor():
    """
    1. Create new supervisor config file
    2. Copy local config to remote config
    3. Register new command
    """
    if exists('/etc/supervisor/conf.d/%s.conf' % project) is False:
        with lcd(local_config_dir):
            with cd(remote_supervisor_dir):
                put('./%s.conf' % project, './', use_sudo=True)
                sudo('supervisorctl reread')
                sudo('supervisorctl update')


def configure_git():
    """
    1. Setup bare Git repo
    2. Create post-receive hook
    """
    if exists(remote_git_dir) is False:
        sudo('mkdir ' + remote_git_dir)
        sudo('chown {u}:{u} {d}'.format(u=env.user, d=remote_git_dir))
        with cd(remote_git_dir):
            run('mkdir %s.git' % project)
            with cd('%s.git' % project):
                run('git init --bare')
                with lcd(local_config_dir):
                    with cd('hooks'):
                        put('./post-receive', './', use_sudo=False)
                        sudo('chmod +x post-receive')


def run_app():
    """ Run the app! """
    with cd(remote_flask_dir):
        sudo('supervisorctl start %s' % project)

def stop_app():
    """ Run the app! """
    with cd(remote_flask_dir):
        sudo('supervisorctl stop %s' % project)


def deploy():
    """
    1. Copy new Flask files
    2. Restart gunicorn via supervisor
    """
    with lcd(local_app_dir):
        local('git add -A')
        commit_message = prompt("Commit message?")
        local('git commit -am "{0}"'.format(commit_message))
        local('git push production master')
        sudo('supervisorctl restart %s' % project)

def restart():
        sudo('supervisorctl restart %s' % project)


def rollback():
    """
    1. Quick rollback in case of error
    2. Restart gunicorn via supervisor
    """
    with lcd(local_app_dir):
        local('git revert master  --no-edit')
        local('git push production master')
        sudo('supervisorctl restart %s' % project)


def status():
    """ Is our app live? """
    sudo('supervisorctl status')


def create():
    install_requirements()
    install_flask()
    configure_nginx()
    configure_supervisor()
    configure_git()

def clean():
    stop_app()
    sudo('rm -rf %s' % remote_app_dir)
    sudo('rm -rf %s' % remote_git_dir)
    sudo('rm -f /etc/supervisor/conf.d/%s.conf' % project)
    sudo('rm -f /etc/nginx/sites-available/%s % project')
    sudo('rm -f /etc/nginx/sites-enabled/%s % project')
