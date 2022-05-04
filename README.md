# flask-deploy

Deploy a flask project by setting up a remote ubuntu server from scratch

    fab create flask_project app 8000
    
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
      print-site-dir
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


## add-remote

    $ fab -H deployhost add-remote foo.bar
    
Issues command
    $ git remote add foo.bar user@deployhost:/home/www/sites/foo.bar/git

    $ git remote -v
    foo.bar    user@deployhost:/home/www/sites/foo.bar/git (fetch)
    foo.bar    user@deployhost:/home/www/sites/foo.bar/git (push)
    
## clean

Removes all configuration on deploy host for site

    $ fab -H deployhost clean foo.bar
    
executes on deployhost

    $ rm -rf /home/www/sites/foo.bar
    $ rm -f /etc/supervisor/conf.d/foo.bar.conf
    $ rm -f /etc/nginx/sites-available/foo.bar
    $ rm -f /etc/nginx/sites-enabled/foo.bar


## hello

    $ fab -H localhost hello
    Hello world!
    
    
## print-site-dir

    $ fab -H localhost print-site-dir foo.bar
    /home/www/sites/foo.bar

Check out the blog post: https://realpython.com/blog/python/kickstarting-flask-on-ubuntu-setup-and-deployment/
