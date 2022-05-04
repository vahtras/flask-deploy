from unittest.mock import patch, call, MagicMock
import textwrap

import fabfile


@patch('fabfile.DEPLOY_ROOT', '/www')
@patch('fabfile.SERVER_IP', '123.456.789.00')
@patch('fabfile.DEPLOY_USER', 'whom')
@patch('fabfile.DEPLOY_HOST', 'where')
@patch('invoke.tasks.isinstance')  # necessary for mocking
@patch('fabfile.exists')
class TestFab:

    def setup(self):
        self.c = MagicMock()

    def test_hello(self, *args):
        fabfile.hello(self.c)
        self.c.run.assert_called_once_with('echo "Hello world!"')

###########
# install #
###########

    def test_site_dir(self, *args):
        fabfile.install_site_dir(self.c, 'foo.bar')
        self.c.run.assert_called_once_with('mkdir -p /www/sites/foo.bar')

    def test_install_venv(self, *args):
        fabfile.install_venv(self.c, 'foo.bar')
        self.c.run.assert_called_once_with(textwrap.dedent(
            """\
            virtualenv /www/sites/foo.bar/venv3 -p python3
            source /www/sites/foo.bar/venv3/bin/activate
            pip install -r /www/sites/foo.bar/requirements.txt
            """
        ))
#######
# git #
#######

    def test_configure_git_exists(self, *args):
        exists, _ = args
        exists.side_effect = [True, True]

        with patch('fabfile.exists') as mock_exists:
            with patch('fabfile.print') as mock_print:
                mock_exists.return_value = True
                fabfile.configure_git(self.c, 'foo.bar')

        mock_print.assert_called_once_with(
            '/www/sites/foo.bar/git already exists'
        )
        self.c.sudo.assert_not_called()
        self.c.cd.assert_not_called()
        self.c.run.assert_not_called()

    def test_configure_git_new(self, *args):
        exists, _ = args
        exists.side_effect = [False, False]

        fabfile.configure_git(self.c, 'foo.bar')

        post_receive_file = '/www/sites/foo.bar/git/hooks/post-receive'
        post_receive_cmd = "#!/bin/sh\nGIT_WORK_TREE=/www/sites/foo.bar/src git checkout --recurse-submodules -f"
        self.c.run.assert_has_calls([
            call('git init --bare /www/sites/foo.bar/git'),
            call('echo "%s" > %s' % (post_receive_cmd, post_receive_file)),
            call(f'chmod +x {post_receive_file}')
        ])

    def test_remote_git_dir(self, *args):
        assert fabfile.remote_git_dir('foo.bar') == '/www/sites/foo.bar/git'

    def test_add_remote(self, *args):
        with patch('fabfile.subprocess.run') as fsr:
            fabfile.add_remote(
                self.c, 'foo.bar', deploy_user='whom', deploy_host='where'
            )
        fsr.assert_called_once_with(
            'git remote add foo.bar whom@where:/www/sites/foo.bar/git',
            shell=True, check=True
        )

    def test_add_existing_remote(self, *args):
        with patch('fabfile.subprocess.run') as fsr:
            fsr.side_effect = fabfile.subprocess.CalledProcessError(1, 'yo')
            with patch('fabfile.print') as fp:
                fabfile.add_remote(self.c, 'foo.bar')
        fp.assert_called_once_with('Remote repository foo.bar exists')

    def test_add_remote_other(self, *args):
        with patch('fabfile.subprocess.run') as fsr:
            fabfile.add_remote(
                self.c, 'foo.bar', deploy_user='whom', deploy_host='test.site'
            )
        fsr.assert_called_once_with(
            'git remote add foo.bar whom@test.site:/www/sites/foo.bar/git',
            shell=True, check=True
        )

    def test_push_remote(self, *args):
        with patch('fabfile.subprocess.run') as fsr:
            fabfile.push_remote(self.c, 'foo.bar')
        fsr.assert_called_once_with(
            'git push foo.bar master:master',
            shell=True
        )

#########
# flask #
#########

    def test_install_flask_and_exists(self, *args):
        exists, _ = args
        exists.return_value = True

        with patch('fabfile.install_root'):
            with patch('fabfile.print') as p:
                fabfile.install_flask(self.c, 'foo.bar')
        self.c.run.assert_not_called()
        p.assert_called_once_with('/www/sites/foo.bar/src exists')

    def test_install_flask_and_not_exists(self, *args):
        exists, _ = args
        exists.return_value = False

        with patch('fabfile.install_root'):
            with patch('fabfile.install_venv'):
                fabfile.install_flask(self.c, 'foo.bar')
        self.c.run.assert_has_calls([
            call("mkdir -p /www/sites/foo.bar/src"),
            call(
                "ln -sf  /www/sites/foo.bar/src/app/static"
                " /www/sites/foo.bar/static"
            ),
        ])

    def test_remote_flask_dir(self, *args):
        assert fabfile.remote_flask_dir('foo.bar') == '/www/sites/foo.bar/src'

    def test_install_root(self, *args):
        exists, _ = args
        exists.return_value = False
        fabfile.install_root(self.c)
        self.c.sudo.assert_has_calls([
            call('mkdir -p /www'),
            call('chown whom:whom /www'),
        ])

    def test_remote_site(self, *args):
        assert fabfile.remote_site_dir('foo.bar') == '/www/sites/foo.bar'

#########
# nginx #
#########

    def test_configure_nginx(self, *args):
        exists, _ = args
        exists.side_effect = [True, True]

        with patch('fabfile.disable_nginx_default'):
            fabfile.configure_nginx(self.c, 'foo.bar')

        self.c.sudo.assert_has_calls([
            call('/etc/init.d/nginx start'),
            call('mv /tmp/foo.bar /etc/nginx/sites-available/foo.bar'),
            call('/etc/init.d/nginx restart'),
        ])

        self.c.put.assert_called_with(
            './sites/foo.bar/etc/nginx/sites-available/foo.bar',
            '/tmp/foo.bar'
        )

    def test_disable_default(self, *args):
        exists, _ = args

        exists.return_value = False
        fabfile.disable_nginx_default(self.c)
        self.c.sudo.assert_not_called()

        exists.return_value = True
        fabfile.disable_nginx_default(self.c)
        self.c.sudo.assert_called_once_with(
            'rm /etc/nginx/sites-enabled/default'
        )

    def test_setup_link(self, *args):
        fabfile.enable_link(self.c, 'foo.bar')
        self.c.sudo.assert_has_calls([
            call('touch /etc/nginx/sites-available/foo.bar'),
            call(
                'ln -s /etc/nginx/sites-available/foo.bar'
                ' /etc/nginx/sites-enabled/foo.bar'
            ),
        ])

    def test_scp(self, *args):
        fabfile.scp(self.c, 'foo', '/bar/baz')
        self.c.put.assert_called_once_with('foo', '/tmp/baz')
        self.c.sudo.assert_called_once_with('mv /tmp/baz /bar/baz')

##############
# supervisor #
##############

    def test_configure_supervisor1(self, *args):
        exists, _ = args
        exists.return_value = True

        fabfile.configure_supervisor(self.c, 'foo.bar')

        self.c.sudo.assert_not_called()
        self.c.cd.assert_not_called()
        self.c.put.assert_not_called()

        exists.return_value = False

        fabfile.configure_supervisor(self.c, 'foo.bar')

        self.c.put.assert_called_with(
            './sites/foo.bar/etc/supervisor/conf.d/foo.bar.conf',
            '/tmp/foo.bar.conf'
        )
        self.c.sudo.assert_has_calls([
            call('mv /tmp/foo.bar.conf /etc/supervisor/conf.d/foo.bar.conf'),
            call('supervisorctl reread'),
            call('supervisorctl update'),
        ])

    def test_run(self, *args):
        fabfile.start_app(self.c, 'foo.bar')
        self.c.sudo.assert_called_once_with('supervisorctl start foo.bar')

    def test_stop(self, *args):
        fabfile.stop_app(self.c, 'foo.bar')
        self.c.sudo.assert_called_once_with('supervisorctl stop foo.bar')

    def test_status(self, *args):
        fabfile.status(self.c)
        self.c.sudo.assert_called_once_with('supervisorctl status')

##########
# deploy #
##########

    def test_deploy(self, *args):
        with patch('fabfile.start_app') as mrun:
            with patch('fabfile.stop_app') as mstop:
                fabfile.restart_app(self.c, 'foo.bar')
        mrun.assert_called_once_with(self.c, 'foo.bar')
        mstop.assert_called_once_with(self.c, 'foo.bar')

    def test_rollback(self, *args):

        fabfile.rollback(self.c, 'foo.bar')

        self.c.local.assert_has_calls([
            call('git revert master --no-edit'),
            call('git push foo.bar master')
        ])
        self.c.sudo.assert_called_once_with('supervisorctl restart foo.bar')

###########
# certbot #
###########

    def test_install_certbot(self, *args):
        fabfile.install_certbot(self.c)
        self.c.sudo.assert_has_calls([
            call('apt-get update'),
            call('apt-get install python-certbot-nginx'),
        ])

    def test_install_cert(self, *args):
        fabfile.install_cert(self.c)
        self.c.sudo.assert_called_once_with(
            'certbot --nginx'
        )

#############
# uninstall #
#############

    def test_clean(self, *args):

        fabfile.clean(self.c, 'foo.bar')

        self.c.sudo.assert_has_calls([
            call('supervisorctl stop foo.bar'),
            call('rm -rf /www/sites/foo.bar'),
            call('rm -f /etc/supervisor/conf.d/foo.bar.conf'),
            call('rm -f /etc/nginx/sites-available/foo.bar'),
            call('rm -f /etc/nginx/sites-enabled/foo.bar'),
        ])

# env

    def test_env_cmd(self, *args):
        fabfile.remote_env_cmd(self.c, "FOO=BAR", "printenv FOO")
        self.c.run.assert_called_once_with('FOO=BAR printenv FOO')

    def test_env_sudo(self, *args):
        fabfile.remote_env_sudo(self.c, "FOO=BAR", "printenv FOO")
        self.c.sudo.assert_called_once_with('FOO=BAR printenv FOO')
