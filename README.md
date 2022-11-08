# flask-deploy

Deploy a flask project by setting up a remote ubuntu server from scratch,
originally based on a [realpython blog post](https://realpython.com/blog/python/kickstarting-flask-on-ubuntu-setup-and-deployment)

## Content

Available tasks:

    $ fab -l
      add-remote                 Define remote repo for site to track
      clean                      Clear a configuration from server
      configure-git              1. Setup bare Git repo
      configure-nginx            Configure nginx
      configure-supervisor       Configure supervisor for nginx
      create                     Install a deployment from scratch
      deploy                     1. Copy new Flask files
      disable-nginx-default
      enable-link
      generate-site-nginx        Generate configuration files for nginx
      generate-site-supervisor   Generate configuration files for
                                 supervisor/gunicorn
      hello
      hi
      install-cert               Generate and install letsencrypt cert
      install-certbot            Install certbot for letsencrypt
      install-flask              Install Flask project
      install-requirements       Install required packages.
      install-root               Install root install directory
      install-site-dir
      install-venv
      push-remote                Push to  remote repo
      reload-supervisor
      remote-env-cmd
      remote-env-sudo
      restart-all
      restart-app
      restart-nginx
      rollback                   1. Quick rollback in case of error
      scp
      start-app                  Run the app!
      status                     Is our app live?
      stop-app                   Stop the app!

## Conventions

    In this document "$ " designates shell prompt on localhost and "% " shell
    prompt on deployhost.

## add-remote

    $ fab -H deployhost add-remote foo.bar
    
Issues command locally (setting up remote repo on localhost)

    % git remote add foo.bar user@deployhost:/home/www/sites/foo.bar/git

    % git remote -v
    foo.bar    user@deployhost:/home/www/sites/foo.bar/git (fetch)
    foo.bar    user@deployhost:/home/www/sites/foo.bar/git (push)
    
## clean

Removes all configuration on deploy host for site

    $ fab -H deployhost clean foo.bar
    
executes on deployhost

    % rm -rf /home/www/sites/foo.bar
    % rm -f /etc/supervisor/conf.d/foo.bar.conf
    % rm -f /etc/nginx/sites-available/foo.bar
    % rm -f /etc/nginx/sites-enabled/foo.bar


## hello

    $ fab hello
    Hello world!
    

## configure-git

    $ fab -H deployhost configure-git foo.bar
    
runs

    $ git init --bare /www/sites/foo.bar/git
    $ echo > /home/www/sites/foo.bar/git/hooks/post-receive << EOF
    #!/bin/sh
    GIT_WORK_TREE=/home/www/sites/foo.bar/src git checkout --recurse-submodules -f
    EOF
    $ chmod +x /home/www/sites/foo.bar/git/hooks/post-receive
    
## configure-nginx

    $ fab -H deployhost configure-nginx foo.bar
    
runs
    
    % sudo /etc/init.d/nginx start
    % sudo rm /etc/nginx/sites-enabled/default
    $ scp ./sites/foo.bar/etc/nginx/sites-available/foo.bar /etc/nginx/sites-available/foo.bar
    % sudo ln -s /etc/nginx/sites-available/foo.bar /etc/nginx/sites-enabled/foo.bar
    % sudo /etc/init.d/nginx restart
    
    
## configure-supervisor

    $ fab -H deployhost configure-supervisor foo.bar
    
runs

    > scp ./sites/foo.bar/etc/supervisor/conf.d/foo.bar.conf deployhost:/etc/supervisor/conf.d/
    $ sudo supervisorctl reread
    $ sudo supervisorctl update
    
            
    
## create

    runs complete deployment from scratch
    
    $ fab -H deployhost create foo.bar proj app 8000
    
is equivalent to (see individual commands for detail

    $ fab -H deployhost configure-git foo.bar
    $ fab -H deployhost install-flask foo.bar app
    $ fab -H deployhost add-remote foo.bar
    $ fab -H deployhost push-remote foo.bar
    $ fab -H deployhost generate-site-nginx foo.bar 8000
    $ fab -H deployhost configure-nginx foo.bar
    $ fab -H deployhost generate-site-supervisor foo.bar proj app 8000
    $ fab -H deployhost configure-supervisor foo.bar
    $ fab -H deployhost start-app foo.bar
    $ fab -H deployhost install-cert
    
## deploy

Save/commit changes and, to deployhost and restart with supervisorctl

    $ fab -H deployhost app --repo production
    
runs
    $ git add -A
    $ git commit -am commit_message
    $ git push production master
    $ sudo supervisorctl
    
## disable-nginx-default

    $ fab -H deployhost disable-nginx-default

runs

    $ sudo rm -f /etc/nginx/sites-enabled/default

## enable-link

    $ fab -H deployhost enble-link foo.bar
    
runs

    $ ln -s /etc/nginx/sites-available/foo.bar /etc/nginx/sites-enabled/foo.bar
    
## generate-site-nginx

    Generate configuration files for nginx

    $ fab generate-site-nginx foo.bar
    
runs

    $ mkdir sites/foo.bar/etc/nginx/sites-available
    
    sites
    └── foo.bar
        └── etc
            └── nginx
                └── sites-available

    $ cat >> sites/foo.bar/etc/nginx/sites-available/foo.bar << EOF
    server {
        server_name foo.bar;
        location / {
            proxy_pass htp://localhost:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
        location_static {
            alias /home/www/sites/foo.bar/static;
        }
    }
    EOF
    
## generate-site-supervisor

Creates locally

    sites
    └── foo.bar
        └── etc
            ├── nginx
            │   └── sites-available
            │       └── foo.bar
            └── supervisor
                └── conf.d
                    └── foo.bar.conf

with

    foo.bar.conf:
    [program:foo.bar]
    command = /home/www/sites/foo.bar/venv3/bin/gunicorn flask_project:app -b localhost:8000
    directory = /home/www/sites/foo.bar/src
    user = user

## install-cert

    $ fab -H deployhost install-cert
    
runs

    % sudo certbot --nginx
    
## install-flask

    $ fab -H deployhost install-flask foo.bar
    
runs
    
    % ln -sf /home/www/sites/foo.bar/src/app/static /home/www/sites/foo.bar/static
    $ fab install_venv foo.bar
    
    
    
## install-requirements

Installs packages on deploy host os

    $ fab -H deployhost install-requirements
    
runs

    % sudo apt update
    % sudo apt install -y python3 python3-pip python3-virtualenv nginx supervisor git python-certbot-nginx

## install-root

    $ fab -H deployhost install_root
    
runx

    % sudo  mkdir -p /home/www
    % sudo chown user:user /home/www
    
## install-site-dir

    $ fab install-site-dir foo.bar

    % mkdir -p /home/www/sites/foo.bar
    
## install-venv

    $ fab -H deployhost install-venv foo.bar
    
    % scp requirements.txt deployhost:/home/www/sites/foo.bar/
    
    
## push-remote

    $ fab push-remote foo.bar
    
    $ git push foo.bar master:master

## reload-supervisor

    $ fab reload-supervisor
    
    % sudo supervisorctl reread
    % sudo supervisorctl update
    
## remote-env-cmd

    $ fab remote-env-cmd foo=bar  cmd
    
    % foo=bar cmd
    
## remote-env-sudo

    $ fab remote-env-sudo foo=bar  cmd
    
    % sudo foo=bar cmd
   
## restart-app

    $ fab restart-app foo.bar
    
    % sudo supervisorctl stop foo.bar
    % sudo supervisorctl start foo.bar
    
## restart-nginx

    $ fab restart-nginx
    
    % sudo /etc/init.d/nginx restart
    
## rollback

    $ fab rollback foo.bar
    
    $ git revert master --no-edit
    $ git push foo.bar master
    % sudo supervisorctl restart foo.bar
    
## scp

    $ fab -H deployhost scp source target
    
    $ scp source deployhost:target
    
## start-app

    $ fab start-app foo.bar
    
    % sudo supervisorctl start foo.bar
    
## status

    $ fab status foo.bar
    
    % sudo supervisorctl statuas foo.bar
    
## stop-app

    $ fab stop-app foo.bar
    
    % sudo supervisorctl stop foo.bar
