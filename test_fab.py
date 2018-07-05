import unittest
import pytest
import sys
try:
    from unittest.mock import patch, call, mock_open, MagicMock
except ImportError:
    from mock import patch, call, mock_open, MagicMock


from fabfile import *

@patch('fabfile.REMOTE_ROOT', '/www')
@patch('fabfile.SERVER_IP', '123.456.789.00')
@patch('fabfile.user', 'whom')
@patch('invoke.tasks.isinstance') # necessary for mocking
@patch('fabfile.exists')
class TestFab(unittest.TestCase):

    def setUp(self):
        self.c = MagicMock()

    def test_hello(self, *args):
        hello(self.c)
        self.c.run.assert_called_once_with('echo "Hello world!"')

###########
# install #
###########

    def test_create(self, *args):
        with patch('fabfile.install_requirements') as m_inst_req:
            create(self.c, 'foo.bar')
            m_inst_req.assert_called_once_with(self.c)

    def test_site_dir(self, *args):
        install_site_dir(self.c, 'foo.bar')
        self.c.run.assert_called_once_with(f'mkdir -p /www/sites/foo.bar')

    def test_install_venv(self, *args):
        install_venv(self.c, 'foo.bar')
        self.c.run.assert_called_once_with(f"""\
virtualenv /www/sites/foo.bar/venv3
source /www/sites/foo.bar/venv3/bin/activate
pip install Flask
"""
        )
        
#######
# git #    
#######

    def test_configure_git(self, *args):
        exists, _ = args
        exists.side_effect = [True, True]

        configure_git(self.c, 'foo.bar')

        self.c.sudo.assert_not_called()
        self.c.cd.assert_not_called()
        self.c.run.assert_not_called()
        
        exists.side_effect = [False, False]

        configure_git(self.c, 'foo.bar')

        post_receive_file = '/www/sites/foo.bar/git/hooks/post-receive'
        post_receive_cmd = "#!/bin/sh\nGIT_WORK_TREE=/www/sites/foo.bar/src git checkout -f"
        self.c.run.assert_has_calls([
            call('git init --bare /www/sites/foo.bar/git'),
            call('echo "%s" > %s' % (post_receive_cmd, post_receive_file)),
            call(f'chmod +x {post_receive_file}')
        ])

    @pytest.mark.skip()
    def test_remote_git_root(self, *args):
        exists, _ = args

        exists.return_value
        create_git_root(self.c)
        self.c.sudo.assert_not_called()

        exists.return_value = False
        create_git_root(self.c)
        self.c.sudo.assert_has_calls([
            call('mkdir -p /git'),
            call('chown whom:whom /git'),
        ])

    def test_remote_git_dir(self, *args):
        assert remote_git_dir('foo.bar')  == '/www/sites/foo.bar/git'

#########
# flask #
#########


    def test_install_flask_and_exists(self, *args):
        exists, _ = args
        exists.return_value = True

        with patch('fabfile.install_root'):
            with patch('fabfile.print') as p:
                install_flask(self.c, 'foo.bar')
        self.c.run.assert_not_called()
        p.assert_called_once_with('/www/sites/foo.bar/src exists')

    def test_install_flask_and_not_exists(self, *args):
        exists, _ = args
        exists.return_value = False

        with patch('fabfile.install_root'):
            install_flask(self.c, 'foo.bar')
        self.c.run.assert_has_calls([
            call("mkdir -p /www/sites/foo.bar/src"),
            call("""\
virtualenv venv3 -p python3
source venv3/bin/activate
pip install Flask
"""
            ),
        ])

    def test_remote_flask_dir(self, *args):
        assert remote_flask_dir('foo.bar') == '/www/sites/foo.bar/src'

    def test_install_root(self, *args):
        exists, _ = args
        exists.return_value = False
        install_root(self.c)
        self.c.sudo.assert_has_calls([
            call(f'mkdir -p /www'),
            call(f'chown whom:whom /www'),
        ])

    def test_remote_site(self, *args):
        assert remote_site_dir('foo.bar') == '/www/sites/foo.bar'
        

#########
# nginx #
#########

    def test_configure_nginx(self, *args):
        exists, _ = args
        exists.side_effect=[True, True]

        with patch('fabfile.disable_nginx_default'):
            configure_nginx(self.c, 'foo.bar')

        self.c.sudo.assert_has_calls([
            call('/etc/init.d/nginx start'),
            call('mv /tmp/foo.bar /etc/nginx/sites-available/foo.bar'),
            call('/etc/init.d/nginx restart'),
        ])

        self.c.put.assert_called_with(
            f'./sites/foo.bar/etc/nginx/sites-available/foo.bar',
            '/tmp/foo.bar'
        )


    def test_disable_default(self, *args):
        exists, _ = args

        exists.return_value = False
        disable_nginx_default(self.c)
        self.c.sudo.assert_not_called()

        exists.return_value = True
        disable_nginx_default(self.c)
        self.c.sudo.assert_called_once_with(
            'rm /etc/nginx/sites-enabled/default'
        )

    def test_setup_link(self, *args):
        enable_link(self.c, 'foo.bar')
        self.c.sudo.assert_has_calls([
            call('touch /etc/nginx/sites-available/foo.bar'),
            call(
                'ln -s /etc/nginx/sites-available/foo.bar'
                ' /etc/nginx/sites-enabled/foo.bar'
            ),
        ])
        
        

    def test_scp(self, *args):
        scp(self.c, 'foo', '/bar/baz')
        self.c.put.assert_called_once_with('foo', '/tmp/baz')
        self.c.sudo.assert_called_once_with('mv /tmp/baz /bar/baz')

##############
# supervisor #
##############

    def test_configure_supervisor1(self, *args):
        exists, _ = args
        exists.return_value = True

        configure_supervisor(self.c, 'foo.bar')

        self.c.sudo.assert_not_called()
        self.c.cd.assert_not_called()
        self.c.put.assert_not_called()

        exists.return_value = False

        configure_supervisor(self.c, 'foo.bar')

        self.c.put.assert_called_with(
            './config/sites/foo.bar/etc/supervisor/conf.d/foo.bar.conf',
            '/tmp/foo.bar.conf'
        )
        self.c.sudo.assert_has_calls([
            call('mv /tmp/foo.bar.conf /etc/supervisor/conf.d/foo.bar.conf'),
            call('supervisorctl reread'),
            call('supervisorctl update'),
        ])




    def test_run(self, *args):

        run_app(self.c, 'foo.bar')
        self.c.sudo.assert_called_once_with('supervisorctl start foo.bar')

    def test_stop(self, *args):

        stop_app(self.c, 'foo.bar')
        self.c.sudo.assert_called_once_with('supervisorctl stop foo.bar')

    def test_status(self, *args):
        status(self.c)
        self.c.sudo.assert_called_once_with('supervisorctl status')

##########
# deploy #
##########

    def test_deploy(self, *args):
        with patch('fabfile.run_app') as mrun:
            with patch('fabfile.stop_app') as mstop:
                restart(self.c, 'foo.bar')
        mrun.assert_called_once_with(self.c, 'foo.bar')
        mstop.assert_called_once_with(self.c, 'foo.bar')

    def test_rollback(self, *args):

        rollback(self.c, 'foo.bar')

        self.c.local.assert_has_calls([
            call('git revert master --no-edit'),
            call('git push foo.bar master')
        ])
        self.c.sudo.assert_called_once_with('supervisorctl restart foo.bar')




###########
# certbot #
###########

    def test_install_certbot(self, *args):
        install_certbot(self.c)
        self.c.sudo.assert_has_calls([
            call('apt-get update'),
            call('apt-get install python-certbot-nginx'),
        ])

    def test_install_cert(self, *args):
        install_cert(self.c)
        self.c.sudo.assert_called_once_with(
            'certbot --nginx'
        )

#############
# uninstall #
#############

    def test_clean(self, *args):

        clean(self.c, 'foo.bar')

        self.c.sudo.assert_has_calls([
            call('supervisorctl stop foo.bar'),
            call('rm -rf /www/sites/foo.bar'),
            call('rm -f /etc/supervisor/conf.d/foo.bar.conf'),
            call('rm -f /etc/nginx/sites-available/foo.bar'),
            call('rm -f /etc/nginx/sites-enabled/foo.bar'),
        ])

    def test_add_remote(self, *args):
        with patch('fabfile.subprocess.run') as fsr:
            add_remote(self.c, 'foo.bar')
        fsr.assert_called_once_with(
            'git remote add foo.bar whom@foo.bar:/www/sites/foo.bar/git',
            shell=True
        )

    def test_add_remote_other(self, *args):
        with patch('fabfile.subprocess.run') as fsr:
            add_remote(self.c, 'foo.bar', 'test.site')
        fsr.assert_called_once_with(
            'git remote add foo.bar whom@test.site:/www/sites/foo.bar/git',
            shell=True
        )

    def test_push_remote(self, *args):
        with patch('fabfile.subprocess.run') as fsr:
            push_remote(self.c, 'foo.bar')
        fsr.assert_called_once_with(
            'git push foo.bar master:master',
            shell=True
        )

#
# save
#        self.c.local.assert_has_calls([
#            call("git remote get-url production || \
#git remote add production whom@123.456.789.00:/www/sites/foo.bar.git"),
#            call("git push production master"),
#        ])
