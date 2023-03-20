###############
#   imports   #
###############

import os
import pathlib
import subprocess
import textwrap


from invoke import task, run as local
from patchwork.files import exists

from file_and_stream import logger

##############
#   config   #
##############


DEPLOY_ROOT = "/home/www"
DEPLOY_USER = os.environ.get('DEPLOY_USER', 'user')
DEPLOY_HOST = os.environ.get('DEPLOY_HOST', 'deployhost')
DEPLOY_SERVER = os.environ.get('DEPLOY_SERVER', 'gunicorn')
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
    logger.info('I am the world')
    c.run('echo "Hello world!"')


@task
def hi(c):
    logger.info('hello')
    local('echo "Hello world!"')


@task
def quickstart(c):
    logger.info('quickstart')
    site = input('site:')
    deploy_host = input('Deploy host:')
    deploy_user = input('Deploy user:')
    module = input('Module:')
    app = input('App:')
    port = input('Port:')
    with open('.envrc', 'a') as envrc:
        envrc.write(f'export DEPLOY_HOST={deploy_host}\n')
        envrc.write(f'export DEPLOY_USER={deploy_user}\n')
        envrc.write(f'export FLASK_MODULE={module}\n')
        envrc.write(f'export APP={app}\n')
        envrc.write(f'export PORT={port}\n')
        envrc.write(f'export SITE={site}\n')
        envrc.write('export PYTHONPATH=flask-deploy\n')
    local('direnv allow')


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
    logger.info('Create from scratch')
    # install_requirements(c)
    configure_git(c, site, branch='master')
    install_flask_work_tree(c, site, package=app)
    install_venv(c, site, version=3)
    add_remote(c, site, deploy_user=DEPLOY_USER, deploy_host=DEPLOY_HOST)
    push_remote(c, site, branch='master', force=False)
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
def install_venv(c, site, version="3"):
    """
    Initialize virtual environment on deploy site
    """
    logger.info('Install virtual env')
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
    logger.info('Configure git')

    if not pathlib.Path('.git').is_dir():
        logger.info("Initializing git locally first")
        local("git init .")
        local('echo *.pyc > .gitignore')
        local('echo *.log >> .gitignore')
        local('echo .envrc >> .gitignore')
        local('echo flask-deploy >> .gitignore')
        local('echo fabfile.py >> .gitignore')
        local('git add .gitignore')

        files = [
            "app.py", "main.py", "config.py", "requirements.txt",
            "requirements-dev.txt", "Makefile",
        ]
        dirs = ["app", "templates", "tests"]
        for f in files:
            local(f'test -f {f} && git add {f} || :')
        for d in dirs:
            local(f'test -d {d} && git add {d} || :')

        local("git commit -am 'initialize git'")

    assert_clean_workdir()

    remote = remote_git_dir(site)
    if exists(c, remote):
        logger.info(f"{remote} already exists")
    else:
        logger.info("Creating: " + remote)
        c.run(f"git init --bare {remote}")
        c.run(
            'echo "#!/bin/sh\n'
            f"GIT_WORK_TREE={remote_flask_work_tree(site)}"
            f' git checkout {branch} --recurse-submodules -f"'
            f' > {remote}/hooks/post-receive'
        )
        c.run(f"chmod +x {remote_git_dir(site)}/hooks/post-receive")

def assert_clean_workdir():
    git_status = local('git status', hide=True)
    if "working tree clean" not in git_status.stdout:
        logger.info("Local repository not clean")
        print()
        print(textwrap.indent(git_status.stdout, '    '))
        print("Untracked files present - save to git before continuing")
        exit()

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
    logger.info('Install Flask work tree')

    if exists(c, remote_flask_work_tree(site)):
        logger.info(f"{remote_flask_work_tree(site)} exists")
    else:
        c.run(f"mkdir -p {remote_flask_work_tree(site)}")
        c.run(
            "ln -sf"
            f"  {remote_flask_work_tree(site)}/{package}/static"
            f" {remote_site_dir(site)}/static"
        )


@task
def install_root(c):
    """
    Install root install directory
    """
    if exists(c, DEPLOY_ROOT):
        logger.info(DEPLOY_ROOT)
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
    logger.info('Configure nginx')
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
    logger.info('Configure supervisor')

    if exists(c, f"/etc/supervisor/conf.d/{site}.conf") is False:
        c.put(
            f"./sites/{site}/etc/supervisor/conf.d/{site}.conf",
            f"/tmp/{site}.conf"
        )
        c.sudo(f"mv /tmp/{site}.conf /etc/supervisor/conf.d/{site}.conf")
        c.sudo("supervisorctl reread")
        c.sudo("supervisorctl update")
    else:
        logger.info(f"/etc/supervisor/conf.d/{site}.conf already exists")


@task
def reload_supervisor(c):
    c.sudo("supervisorctl reread")
    c.sudo("supervisorctl update")


@task
def start_app(c, site):
    """
    Run the app!
    """
    logger.info('Start app')
    c.sudo(f"supervisorctl start {site}")
    c.sudo(f"supervisorctl status {site}")


@task
def stop_app(c, site):
    """
    Stop the app!
    """
    c.sudo(f"supervisorctl stop {site}")


@task
def restart_app(c, site):
    """
    Restart app (with stop/start)
    """
    logger.info(f'Restarting {site}')
    stop_app(c, site)
    reload_supervisor(c)
    start_app(c, site)


@task
def restart_all(c, site):
    """
    Restart nginx and app
    """
    restart_nginx(c)
    reload_supervisor(c)
    restart_app(c, site)


@task
def status(c):
    """
    Check if app is alive
    """
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
    c.sudo("supervisorctl restart %s" % app)


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
def clean_server(c, site):
    """
    Clear a configuration from server
    """
    logger.info('clean up all')
    stop_app(c, site)
    c.sudo(f"rm -rf {remote_site_dir(site)}")
    c.sudo(f"rm -f /etc/supervisor/conf.d/{site}.conf")
    c.sudo(f"rm -f /etc/nginx/sites-available/{site}")
    c.sudo(f"rm -f /etc/nginx/sites-enabled/{site}")
    clean_local(c, site)


@task
def clean_local(c, site):
    local(f'rm -rf sites/{site}')


@task
def install_cert(c, site):
    """
    Generate and install letsencrypt cert
    """
    logger.info('Install cert')
    c.sudo(f"certbot --nginx -d {site} -n")


@task
def generate_site_nginx(c, site, port=8000):
    """
    Generate configuration files for nginx
    """
    from template import NGINX
    logger.info('Generate nginx')

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
    version="3",
    deploy_user=DEPLOY_USER,
    deploy_server=DEPLOY_SERVER,
):
    """
    Generate configuration files for supervisor/gunicorn
    """
    try:
        import flask
        server = flask.__name__
    except ImportError:
        try:
            import fastapi
            server = fastapi.__name__
        except ImportError:
            logger('No framework installed')
            raise

    from template import SUPERVISOR
    logger.info('Generate supervisor')
    bindir = f"{remote_site_dir(site)}/venv{version}/bin"

    try:
        os.makedirs(f"sites/{site}/etc/supervisor/conf.d")
    except FileExistsError:
        pass

    with open(f"sites/{site}/etc/supervisor/conf.d/{site}.conf", "w") as f:
        f.write(
            SUPERVISOR[server].format(
                program=site,
                bin=bindir,
                module=module,
                app=app,
                port=port,
                src=remote_flask_work_tree(site),
                user=deploy_user,
                server=deploy_server,
            )
        )


####


@task
def add_remote(c, site, deploy_user=DEPLOY_USER, deploy_host=DEPLOY_HOST):
    """
    Define remote repo for site to track
    """

    if exists(c, site):
        logger.info(f"{site} already exists")
        return

    logger.info(f'Add remote {site}')
    assert pathlib.Path('.git').is_dir(), (
        'Local git repository not initialized'
    )

    local(
        f"git remote add {site}"
        f" {deploy_user}@{deploy_host}:{remote_git_dir(site)}",
    )


@task
def push_remote(c, site, branch='master', force=False):
    """
    Push to  remote repo
    """
    logger.info('Push to remote')
    push_opts = ""
    if force:
        push_opts = "-f"
    # subprocess.run(f"git push {push_opts} {site} {branch}", shell=True)
    local(f"git push {push_opts} {site} {branch}")


@task
def remote_env_cmd(c, env, cmd):
    c.run(f"{env} {cmd}")


@task
def remote_env_sudo(c, env, cmd):
    c.sudo(f"{env} {cmd}")


@task
def list_ports(c):
    """
    List used ports on deploy hosts
    """
    c.run(
        'grep localhost  /etc/nginx/sites-enabled/*'
        ' | cut -d/ -f 5,7'
        ' | cut -d: -f 4,1'
    )
