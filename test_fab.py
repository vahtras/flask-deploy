import unittest
import pytest
import sys
try:
    from unittest.mock import patch, call, mock_open, MagicMock
except ImportError:
    from mock import patch, call, mock_open, MagicMock


from fabfile import *

#@patch('fabfile.exists')
#@patch('fabfile.sudo')
#@patch('fabfile.local')
#@patch('fabfile.run')
#@patch('fabfile.lcd.assert_not_called()
#@patch('fabfile.cd')
#@patch('fabfile.put')

#@patch('fabfile.c')

@patch('invoke.tasks.isinstance') # necessary for mocking
@patch('fabfile.exists')
class TestFab(unittest.TestCase):

    def setUp(self):
        #i.return_value = True
        self.c = MagicMock()

    def test_hello(self, *args):
        hello(self.c)
        self.c.run.assert_called_once_with('echo "Hello world!"')
    
    def test_install_www(self, *args):
        exists, _ = args
        exists.return_value = False
        install_www(self.c)
        self.c.sudo.assert_has_calls(
            [call('mkdir /home/www'), call('chown olav:olav /home/www')]
        )

    def test_install_flask1(self, *args):
        exists, _ = args
        exists.return_value = False

        install_flask(self.c, 'proj')

        self.c.lcd.assert_not_called()
        assert call('/home/www/proj') in self.c.cd.mock_calls
        assert call('/home/git/proj.git') in self.c.cd.mock_calls
        self.c.run.assert_has_calls([
            call("mkdir -p /home/www/proj"),
            call("""\
virtualenv venv3 -p python3
source venv3/bin/activate
pip install Flask
"""
            ),
        ])
        self.c.local.assert_has_calls([
            call("git remote get-url production || \
git remote add production olav@104.200.38.58:/home/www/proj.git"),
            call("git push production master"),
        ])

    def test_install_flask2(self, *args):
        exists, _ = args
        exists.return_value = False

        install_flask(self.c, 'proj', 'staging')

        self.c.lcd.assert_not_called()
        assert call('/home/www/proj-staging') in self.c.cd.mock_calls
        assert call('/home/git/proj-staging.git') in self.c.cd.mock_calls
        self.c.run.assert_has_calls([
            call("mkdir -p /home/www/proj-staging"),
            call("""\
virtualenv venv3 -p python3
source venv3/bin/activate
pip install Flask
"""
            ),
        ])
        self.c.local.assert_has_calls([
            call("git remote get-url staging || \
git remote add staging olav@104.200.38.58:/home/www/proj-staging.git"),
            call("git push staging master"),
        ])

    def test_confname(self, *args):
        assert conf_name('proj') == 'proj'
        assert conf_name('proj', 'staging') == 'proj-staging'

    def test_configure_nginx1a(self, *args):
        exists, _ = args
        exists.side_effect=[True, True]

        configure_nginx(self.c, 'proj')

        self.c.sudo.assert_has_calls([
            call('/etc/init.d/nginx start'),
            call('rm /etc/nginx/sites-enabled/default'),
            call('mv /tmp/proj /etc/nginx/sites-available/proj'),
            call('/etc/init.d/nginx restart'),
        ])
        self.c.lcd.assert_not_called()
        self.c.cd.assert_called_with('/etc/nginx/sites-available')
        self.c.put.assert_called_with('./config/production/proj', '/tmp/proj')

    def test_configure_nginx2a(self, *args):
        exists, _ = args
        exists.side_effect=[True, True]

        configure_nginx(self.c, 'proj', 'staging')

        self.c.sudo.assert_has_calls([
            call('/etc/init.d/nginx start'),
            call('rm /etc/nginx/sites-enabled/default'),
            call('mv /tmp/proj-staging /etc/nginx/sites-available/proj-staging'),
            call('/etc/init.d/nginx restart'),
        ])
        self.c.lcd.assert_not_called()
        self.c.cd.assert_called_with('/etc/nginx/sites-available')
        self.c.put.assert_called_with('./config/staging/proj-staging', '/tmp/proj-staging')#, use_sudo=True)

    def test_configure_nginx1b(self, *args):
        exists, _ = args
        exists.side_effect=[False, False]

        configure_nginx(self.c, 'proj')

        self.c.sudo.assert_has_calls([
            call('/etc/init.d/nginx start'),
            call('touch /etc/nginx/sites-available/proj'),
            call('ln -s /etc/nginx/sites-available/proj /etc/nginx/sites-enabled/proj'),
            call('mv /tmp/proj /etc/nginx/sites-available/proj'),
            call('/etc/init.d/nginx restart'),
        ])
        self.c.lcd.assert_not_called()
        self.c.cd.assert_called_with('/etc/nginx/sites-available')
        self.c.put.assert_called_with('./config/production/proj', '/tmp/proj')#, use_sudo=True)

    def test_configure_nginx2b(self, *args):
        exists, _ = args
        exists.side_effect=[False, False]

        configure_nginx(self.c, 'proj', 'staging')

        self.c.sudo.assert_has_calls([
            call('/etc/init.d/nginx start'),
            call('touch /etc/nginx/sites-available/proj-staging'),
            call('ln -s /etc/nginx/sites-available/proj-staging /etc/nginx/sites-enabled/proj-staging'),
            call('mv /tmp/proj-staging /etc/nginx/sites-available/proj-staging'),
            call('/etc/init.d/nginx restart'),
        ])
        self.c.lcd.assert_not_called()
        self.c.cd.assert_called_with('/etc/nginx/sites-available')
        self.c.put.assert_called_with('./config/staging/proj-staging', '/tmp/proj-staging')#, use_sudo=True)


    def test_configure_supervisor1(self, *args):
        exists, _ = args
        exists.return_value = True

        configure_supervisor(self.c, 'proj')

        self.c.sudo.assert_not_called()
        self.c.lcd.assert_not_called()
        self.c.cd.assert_not_called()
        self.c.put.assert_not_called()

        exists.return_value = False

        configure_supervisor(self.c, 'proj')

        self.c.lcd.assert_not_called()
        #self.c.cd.assert_called_once_with('/etc/supervisor/conf.d')
        self.c.put.assert_called_with('./config/production/proj.conf', '/tmp/proj.conf')#, use_sudo=True)
        self.c.sudo.assert_has_calls([
            call('mv /tmp/proj.conf /etc/supervisor/conf.d/proj.conf'),
            call('supervisorctl reread'),
            call('supervisorctl update'),
        ])

    def test_configure_supervisor2(self, *args):
        exists, _ = args
        exists.return_value = True

        configure_supervisor(self.c, 'proj', 'staging')

        self.c.sudo.assert_not_called()
        self.c.lcd.assert_not_called()
        self.c.cd.assert_not_called()
        self.c.put.assert_not_called()

        exists.return_value = False
        configure_supervisor(self.c, 'proj', 'staging')

        self.c.lcd.assert_not_called()
        #self.c.cd.assert_called_once_with('/etc/supervisor/conf.d')
        self.c.put.assert_called_with('./config/staging/proj-staging.conf', '/tmp/proj-staging.conf')#, use_sudo=True)
        self.c.sudo.assert_has_calls([
            call('mv /tmp/proj-staging.conf /etc/supervisor/conf.d/proj-staging.conf'),
            call('supervisorctl reread'),
            call('supervisorctl update'),
        ])

    def test_remote_git_dir(self, *args):
        assert remote_git_dir('proj')  == '/home/git/proj.git'
        assert remote_git_dir('proj', 'stag')  == '/home/git/proj-stag.git'

    #@pytest.mark.skip()
    def test_configure_git1(self, *args):
        exists, _ = args
        exists.side_effect = [True, True]

        configure_git(self.c, 'proj')

        self.c.sudo.assert_not_called()
        self.c.cd.assert_not_called()
        self.c.lcd.assert_not_called()
        self.c.run.assert_not_called()
        
        exists.side_effect = [False, False]

        configure_git(self.c, 'proj')

        self.c.sudo.assert_has_calls([
            call('mkdir /home/git'),
            call('chown olav:olav /home/git'),
        ])
        self.c.lcd.assert_not_called()

        post_receive_file = '/home/git/proj.git/hooks/post-receive'
        post_receive_cmd = "#!/bin/sh\nGIT_WORK_TREE=/home/www/proj git checkout -f"
        self.c.run.assert_has_calls([
            call('git init --bare /home/git/proj.git'),
            call('echo "%s" > %s' % (post_receive_cmd, post_receive_file)),
            call(f'chmod +x {post_receive_file}')
        ])


    #@pytest.mark.skip()
    def test_configure_git2(self, *args):
        exists, _ = args
        exists.side_effect = [True, True]

        configure_git(self.c, 'proj', 'staging')

        self.c.sudo.assert_not_called()
        self.c.cd.assert_not_called()
        self.c.lcd.assert_not_called()
        self.c.run.assert_not_called()
        
        exists.side_effect = [False, False]

        configure_git(self.c, 'proj', 'staging')

        self.c.sudo.assert_has_calls([
            call('mkdir /home/git'),
            call('chown olav:olav /home/git'),
        ])
        self.c.lcd.assert_not_called()

        post_receive_file = '/home/git/proj-staging.git/hooks/post-receive'
        post_receive_cmd = "#!/bin/sh\nGIT_WORK_TREE=/home/www/proj-staging git checkout -f"
        self.c.run.assert_has_calls([
            call('git init --bare /home/git/proj-staging.git'),
            call('echo "%s" > %s' % (post_receive_cmd, post_receive_file)),
            call(f'chmod +x {post_receive_file}')
        ])


    def test_run1(self, *args):

        run_app(self.c, 'proj')
        #self.c.cd.assert_called_once_with('/home/www/proj')
        self.c.sudo.assert_called_once_with('supervisorctl start proj')

    def test_run2(self, *args):

        run_app(self.c, 'proj', 'staging')
        #self.c.cd.assert_called_once_with('/home/www/proj-staging')
        self.c.sudo.assert_called_once_with('supervisorctl start proj-staging')

    def test_stop1(self, *args):

        stop_app(self.c, 'proj')
        self.c.sudo.assert_called_once_with('supervisorctl stop proj')

    def test_stop2(self, *args):

        stop_app(self.c, 'proj', 'staging')
        self.c.sudo.assert_called_once_with('supervisorctl stop proj-staging')

    def test_rollback1(self, *args):

        rollback(self.c, 'proj')

        self.c.lcd.assert_not_called()
        self.c.local.assert_has_calls([
            call('git revert master --no-edit'),
            call('git push production master')
        ])
        self.c.sudo.assert_called_once_with('supervisorctl restart proj')

    def test_rollback2(self, *args):

        rollback(self.c, 'proj', 'staging')

        self.c.lcd.assert_not_called()
        self.c.local.assert_has_calls([
            call('git revert master --no-edit'),
            call('git push staging master')
        ])
        self.c.sudo.assert_called_once_with('supervisorctl restart proj-staging')

    def test_status(self, *args):
        status(self.c)
        self.c.sudo.assert_called_once_with('supervisorctl status')

    def test_create1(self, *args):
        create(self.c, 'proj')
        #c.sudo.assert_has_calls(call('apt-get update'))
        assert call('apt-get update') in self.c.sudo.mock_calls

    def test_create2(self, *args):
        create(self.c, 'proj', 'staging')
        #c.sudo.assert_has_calls(call('apt-get update'))
        assert call('apt-get update') in self.c.sudo.mock_calls

    def test_clean1(self, *args):

        clean(self.c, 'proj')

        self.c.sudo.assert_has_calls([
            call('supervisorctl stop proj'),
            call('rm -rf /home/www/proj'),
            call('rm -rf /home/git/proj'),
            call('rm -f /etc/supervisor/conf.d/proj.conf'),
            call('rm -f /etc/nginx/sites-available/proj'),
            call('rm -f /etc/nginx/sites-enabled/proj'),
        ])

    def test_clean2(self, *args):

        clean(self.c, 'proj', 'staging')

        self.c.sudo.assert_has_calls([
            call('supervisorctl stop proj-staging'),
            call('rm -rf /home/www/proj-staging'),
            call('rm -rf /home/git/proj-staging'),
            call('rm -f /etc/supervisor/conf.d/proj-staging.conf'),
            call('rm -f /etc/nginx/sites-available/proj-staging'),
            call('rm -f /etc/nginx/sites-enabled/proj-staging'),
        ])
    
