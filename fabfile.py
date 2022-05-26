###############
#   imports   #
###############

import os
import pathlib
import subprocess
import textwrap

from invoke import task, run as local
from patchwork.files import exists

##############
#   config   #
##############

DEPLOY_ROOT = "/home/www"
DEPLOY_USER = os.environ.get('DEPLOYUSER', 'user')
DEPLOY_HOST = os.environ.get('DEPLOYHOST', 'deployhost')
DEPLOY_NGINX_DIR = "/etc/nginx/sites-available"
DEPLOY_SUPERVISOR_DIR = "/etc/supervisor/conf.d"
FLASK_MODULE = os.environ.get('FLASKMODULE', 'flask_project')
APP = os.environ.get('APP', 'app')
PORT = os.environ.get('PORT', 9000)


def remote_site_dir(site):
    return f"{DEPLOY_ROOT}/sites/{site}"


def remote_git_dir(site):
    return f"{DEPLOY_ROOT}/sites/{site}/git"


def remote_flask_work_tree(site):
    return f"{DEPLOY_ROOT}/sites/{site}/src"


#############
#   tasks   #
#############


@task
def hello(c):
    c.run('echo "Hello world!"')


@task
def hi(c):
    local('echo "Hello world!"')


###########
# install #
###########


@task
def create(
    c, site,
    module=FLASK_MODULE,
    app=APP,
    port=PORT,
    deploy_user=DEPLOY_USER
):
    """
    Install a deployment from scratch
    """
    # install_requirements(c)
    configure_git(c, site, branch='master')
    install_flask_work_tree(c, site, package=app)
    install_venv(c, site, version=3.8)
    add_remote(c, site, deploy_user=DEPLOY_USER, deploy_host=DEPLOY_HOST)
    push_remote(c, site, branch='master')
    generate_site_nginx(c, site, port=port)
    configure_nginx(c, site)
    generate_site_supervisor(c, site, module=module, app=app, port=port)
    configure_supervisor(c, site)
    # start webserver
    start_app(c, site)
    # install certificate from Let's Encrypt
    install_cert(c, site)


@task
def install_requirements(c):
    """
    Install required packages.

    Python
    Gunicorn
    Supervisor
    Git
    """
    c.sudo("apt-get update")
    c.sudo("apt-get install -y python3")
    c.sudo("apt-get install -y python3-pip")
    c.sudo("apt-get install -y nginx")
    c.sudo("apt-get install -y supervisor")
    c.sudo("apt-get install -y git")
    c.sudo("apt-get install python-certbot-nginx")


@task
def install_site_dir(c, site):
    c.run(f"mkdir -p {remote_site_dir(site)}")


@task
def install_venv(c, site, version="3.8"):
    c.put("./requirements.txt", f"{remote_site_dir(site)}/requirements.txt")
    site_dir = f'{remote_site_dir(site)}'
    venv_dir = f'{site_dir}/venv{version}'
    git_dir = f'{site_dir}/git'
    work_dir = f'{site_dir}/src'
    py = f'{venv_dir}/bin/python'
    pip = f'{py} -m pip'
    c.run(textwrap.dedent(
        f"""\
        python{version} -m venv {venv_dir}
        {pip} install --upgrade pip setuptools
        {pip} install -r {remote_site_dir(site)}/requirements.txt
        echo source {venv_dir}/bin/activate > {site_dir}/.envrc
        echo export GIT_DIR={git_dir} >> {site_dir}/.envrc
        echo export GIT_WORK_TREE={work_dir} >> {site_dir}/.envrc
        """
    ))


#######
# git #
#######


@task
def configure_git(c, site, branch='master'):
    """
    1. Setup bare Git repo
    2. Create post-receive hook
    """

    remote = remote_git_dir(site)
    if exists(c, remote):
        print(f"{remote} already exists")
    else:
        print("Creating: " + remote)
        c.run(f"git init --bare {remote}")
        c.run(
            'echo "#!/bin/sh\n'
            f"GIT_WORK_TREE={remote_flask_work_tree(site)}"
            f' git checkout {branch} --recurse-submodules -f" > {remote}/hooks/post-receive'
        )
        c.run(f"chmod +x {remote_git_dir(site)}/hooks/post-receive")


#########
# flask #
#########


@task
def install_flask_work_tree(c, site, package="app"):
    """
    Install Flask project

    1. Create project directories
    2. Create and activate a virtualenv
    3. Checkout from previously configured git repo
    """

    if exists(c, remote_flask_work_tree(site)):
        print(f"{remote_flask_work_tree(site)} exists")
    else:
        c.run(f"mkdir -p {remote_flask_work_tree(site)}")
        c.run(
            f"ln -sf  {remote_flask_work_tree(site)}/{package}/static {remote_site_dir(site)}/static"
        )


@task
def install_root(c):
    """
    Install root install directory
    """
    if exists(c, DEPLOY_ROOT):
        print(DEPLOY_ROOT)
    else:
        c.sudo(f"mkdir -p {DEPLOY_ROOT}")
        c.sudo(f"chown {DEPLOY_USER}:{DEPLOY_USER} {DEPLOY_ROOT}")


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
    c.sudo("/etc/init.d/nginx start")

    disable_nginx_default(c)

    enabled = f"/etc/nginx/sites-enabled/{site}"
    available = f"/etc/nginx/sites-available/{site}"

    if exists(c, enabled) is False:
        c.sudo(f"touch {available}")
        c.sudo(f"ln -s {available} {enabled}")

    scp(c, f"./sites/{site}{available}", available)
    c.sudo("/etc/init.d/nginx restart")


@task
def disable_nginx_default(c):
    if exists(c, "/etc/nginx/sites-enabled/default"):
        c.sudo("rm /etc/nginx/sites-enabled/default")


@task
def restart_nginx(c):
    c.sudo("/etc/init.d/nginx restart")


@task
def enable_link(c, site):
    enabled = f"/etc/nginx/sites-enabled/{site}"
    available = f"/etc/nginx/sites-available/{site}"
    c.sudo(f"touch {available}")
    c.sudo(f"ln -s {available} {enabled}")


@task
def scp(c, source, target):
    file_ = pathlib.Path(target).name
    c.put(source, f"/tmp/{file_}")
    c.sudo(f"mv /tmp/{file_} {target}")


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

    if exists(c, f"/etc/supervisor/conf.d/{site}.conf") is False:
        c.put(f"./sites/{site}/etc/supervisor/conf.d/{site}.conf", f"/tmp/{site}.conf")
        c.sudo(f"mv /tmp/{site}.conf /etc/supervisor/conf.d/{site}.conf")
        c.sudo("supervisorctl reread")
        c.sudo("supervisorctl update")
    else:
        print(f"/etc/supervisor/conf.d/{site}.conf already exists")


@task
def reload_supervisor(c, site):
    c.sudo("supervisorctl reread")
    c.sudo("supervisorctl update")


@task
def start_app(c, site):
    """ Run the app! """
    c.sudo(f"supervisorctl start {site}")


@task
def stop_app(c, site):
    """ Stop the app! """
    c.sudo(f"supervisorctl stop {site}")


@task
def restart_app(c, site):
    stop_app(c, site)
    reload_supervisor(c, site)
    start_app(c, site)


@task
def restart_all(c, site):
    restart_nginx(c)
    restart_app(c, site)


@task
def status(c):
    """ Is our app live? """
    c.sudo("supervisorctl status")


@task
def deploy(c, app, repo="production"):
    """
    1. Copy new Flask files
    2. Restart gunicorn via supervisor
    """
    local("git add -A")
    commit_message = c.prompt("Commit message?")
    local('git commit -am "{0}"'.format(commit_message))
    local("git push %s master" % repo)
    sudo("supervisorctl restart %s" % app)


@task
def rollback(c, site):
    """
    1. Quick rollback in case of error
    2. Restart gunicorn via supervisor
    """
    local("git revert master --no-edit")
    local(f"git push {site} master")
    c.sudo(f"supervisorctl restart {site}")


@task
def clean(c, site):
    """
    Clear a configuration from server
    """
    stop_app(c, site)
    c.sudo(f"rm -rf {remote_site_dir(site)}")
    c.sudo(f"rm -f /etc/supervisor/conf.d/{site}.conf")
    c.sudo(f"rm -f /etc/nginx/sites-available/{site}")
    c.sudo(f"rm -f /etc/nginx/sites-enabled/{site}")
    local(f'git remote remove {site}')
    local(f'rm -rf sites/{site}')


@task
def install_cert(c, site):
    """
    Generate and install letsencrypt cert
    """
    c.sudo(f"certbot --nginx -d {site}")


@task
def generate_site_nginx(c, site, port=8000):
    """
    Generate configuration files for nginx
    """
    from template import NGINX

    # c.local(f'mkdir -p sites/{site}/etc/nginx/sites-available')
    try:
        os.makedirs(f"sites/{site}/etc/nginx/sites-available")
    except FileExistsError:
        pass
    with open(f"sites/{site}/etc/nginx/sites-available/{site}", "w") as f:
        f.write(NGINX.format(server_name=site, root=DEPLOY_ROOT, port=port))


@task
def generate_site_supervisor(
    c, site,
    module="flask_project",
    app="app",
    port=8000,
    version="3.8",
    deploy_user=DEPLOY_USER,
):
    """
    Generate configuration files for supervisor/gunicorn
    """
    from template import SUPERVISOR
    bindir = f"{remote_site_dir(site)}/venv{version}/bin"

    try:
        os.makedirs(f"sites/{site}/etc/supervisor/conf.d")
    except FileExistsError:
        pass

    with open(f"sites/{site}/etc/supervisor/conf.d/{site}.conf", "w") as f:
        f.write(
            SUPERVISOR.format(
                program=site,
                bin=bindir,
                module=module,
                app=app,
                port=port,
                src=remote_flask_work_tree(site),
                user=deploy_user,
            )
        )


####


@task
def add_remote(c, site, deploy_user=DEPLOY_USER, deploy_host=DEPLOY_HOST):
    """
    Define remote repo for site to track
    """
    try:
        subprocess.run(
            f"git remote add {site} {deploy_user}@{deploy_host}:{remote_git_dir(site)}",
            shell=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        print(f"Remote repository {site} exists")


@task
def push_remote(c, site, branch='master'):
    """
    Push to  remote repo
    """
    subprocess.run(f"git push {site} {branch}", shell=True)


@task
def remote_env_cmd(c, env, cmd):
    c.run(f"{env} {cmd}")


@task
def remote_env_sudo(c, env, cmd):
    c.sudo(f"{env} {cmd}")


@task
def list_ports(c):
    c.run('grep localhost  /etc/nginx/sites-enabled/* | cut -d/ -f 5,7 | cut -d: -f 4,1')
