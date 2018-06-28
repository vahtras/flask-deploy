import unittest
import sys
try:
    from unittest.mock import patch, call, mock_open
except ImportError:
    from mock import patch, call, mock_open


from fabfile import *

#@patch('fabfile.exists')
#@patch('fabfile.sudo')
#@patch('fabfile.local')
#@patch('fabfile.run')
#@patch('fabfile.lcd')
#@patch('fabfile.cd')
#@patch('fabfile.put')

@patch('fabfile.c')
class TestFab(unittest.TestCase):

        
    def test_install_www(self, c):
        c.exists.return_value = False
        install_www()
        c.sudo.assert_has_calls(
            [call('mkdir /home/www'), call('chown olav:olav /home/www')]
        )

    def test_install_flask1(self, c):
        c.exists.return_value = False

        install_flask('proj')

        c.lcd.assert_called_once_with('./proj')
        c.cd.assert_called_with('/home/www/proj')
        c.run.assert_has_calls([
            call('mkdir -p /home/www/proj/proj'),
            call('virtualenv venv3 -p python3'),
            call('source venv3/bin/activate'),
            call('pip install Flask==0.10.1'),
        ])
        c.put.assert_called_once_with('*', './proj', use_sudo=False)

    def test_install_flask2(self, c):
        c.exists.return_value = False

        install_flask('proj', 'staging')

        c.lcd.assert_called_once_with('./proj')
        c.cd.assert_called_with('/home/www/proj-staging')
        c.run.assert_has_calls([
            call('mkdir -p /home/www/proj-staging/proj'),
            call('virtualenv venv3 -p python3'),
            call('source venv3/bin/activate'),
            call('pip install Flask==0.10.1'),
        ])
        c.put.assert_called_once_with('*', './proj', use_sudo=False)


    def test_confname(self, c):
        assert conf_name('proj') == 'proj'
        assert conf_name('proj', 'staging') == 'proj-staging'

    def test_configure_nginx1a(self, c):

        c.exists.side_effect=[True, True]
        configure_nginx('proj')

        c.sudo.assert_has_calls([
            call('/etc/init.d/nginx start'),
            call('rm /etc/nginx/sites-enabled/default'),
            call('/etc/init.d/nginx restart'),
        ])
        c.lcd.assert_called_with('./config/production')
        c.cd.assert_called_with('/etc/nginx/sites-available')
        c.put.assert_called_with('proj', './', use_sudo=True)

    def test_configure_nginx2a(self, c):

        c.exists.side_effect=[True, True]
        configure_nginx('proj', 'staging')

        c.sudo.assert_has_calls([
            call('/etc/init.d/nginx start'),
            call('rm /etc/nginx/sites-enabled/default'),
            call('/etc/init.d/nginx restart'),
        ])
        c.lcd.assert_called_with('./config/staging')
        c.cd.assert_called_with('/etc/nginx/sites-available')
        c.put.assert_called_with('proj-staging', './', use_sudo=True)

    def test_configure_nginx1b(self, c):

        c.exists.side_effect=[False, False]
        configure_nginx('proj')
        c.sudo.assert_has_calls([
            call('/etc/init.d/nginx start'),
            call('touch /etc/nginx/sites-available/proj'),
            call('ln -s /etc/nginx/sites-available/proj /etc/nginx/sites-enabled/proj'),
            call('/etc/init.d/nginx restart'),
        ])
        c.lcd.assert_called_with('./config/production')
        c.cd.assert_called_with('/etc/nginx/sites-available')
        c.put.assert_called_with('proj', './', use_sudo=True)

    def test_configure_nginx2b(self, c):

        c.exists.side_effect=[False, False]
        configure_nginx('proj', 'staging')

        c.sudo.assert_has_calls([
            call('/etc/init.d/nginx start'),
            call('touch /etc/nginx/sites-available/proj-staging'),
            call('ln -s /etc/nginx/sites-available/proj-staging /etc/nginx/sites-enabled/proj-staging'),
            call('/etc/init.d/nginx restart'),
        ])
        c.lcd.assert_called_with('./config/staging')
        c.cd.assert_called_with('/etc/nginx/sites-available')
        c.put.assert_called_with('proj-staging', './', use_sudo=True)


    def test_configure_supervisor1(self, c):

        c.exists.return_value = True
        configure_supervisor('proj')

        c.sudo.assert_not_called()
        c.lcd.assert_not_called()
        c.cd.assert_not_called()
        c.put.assert_not_called()

        c.exists.return_value = False
        configure_supervisor('proj')

        c.lcd.assert_called_once_with('./config/production')
        c.cd.assert_called_once_with('/etc/supervisor/conf.d')
        c.put.assert_called_with('proj.conf', './', use_sudo=True)
        c.sudo.assert_called_with('supervisorctl reread && supervisorctl update')

    def test_configure_supervisor2(self, c):

        c.exists.return_value = True
        configure_supervisor('proj', 'staging')

        c.sudo.assert_not_called()
        c.lcd.assert_not_called()
        c.cd.assert_not_called()
        c.put.assert_not_called()

        c.exists.return_value = False
        configure_supervisor('proj', 'staging')

        c.lcd.assert_called_once_with('./config/staging')
        c.cd.assert_called_once_with('/etc/supervisor/conf.d')
        c.put.assert_called_with('proj-staging.conf', './', use_sudo=True)
        c.sudo.assert_called_with('supervisorctl reread && supervisorctl update')

    def test_configure_git1(self, c):

        c.exists.return_value = True
        configure_git('proj')
        c.sudo.assert_not_called()
        c.cd.assert_not_called()
        c.lcd.assert_not_called()
        c.run.assert_not_called()
        
        c.exists.return_value = False
        m = mock_open()
        with patch('fabfile.open', m):
            configure_git('proj')
        m.assert_called_once_with('./config/production/post-receive', 'w')
        m().write.assert_called_once_with(
            '#!/bin/sh\nGIT_WORK_TREE=/home/www/proj git checkout -f\n'
        )

        c.sudo.assert_has_calls([
            call('mkdir /home/git'),
            call('chown olav:olav /home/git'),
            call('chmod +x post-receive')
        ])
        c.lcd.assert_called_once_with('./config/production')

        assert call('/home/git') in c.cd.mock_calls
        assert call('proj.git') in c.cd.mock_calls
        assert call('hooks') in c.cd.mock_calls

        c.run.assert_has_calls([
            call('mkdir proj.git'),
            call('git init --bare'),
        ])

        c.put.assert_called_once_with('./post-receive', './', use_sudo=False)

    def test_configure_git2(self, c):

        c.exists.return_value = True
        configure_git('proj', 'staging')
        c.sudo.assert_not_called()
        c.cd.assert_not_called()
        c.lcd.assert_not_called()
        c.run.assert_not_called()
        
        c.exists.return_value = False
        
        m = mock_open()
        with patch('fabfile.open', m):
            configure_git('proj', 'staging')
        m.assert_called_once_with('./config/staging/post-receive', 'w')
        m().write.assert_called_once_with(
            '#!/bin/sh\nGIT_WORK_TREE=/home/www/proj-staging git checkout -f\n'
        )
        
        c.sudo.assert_has_calls([
            call('mkdir /home/git'),
            call('chown olav:olav /home/git'),
            call('chmod +x post-receive')
        ])
        c.lcd.assert_called_once_with('./config/staging')

        assert call('/home/git') in c.cd.mock_calls
        assert call('proj-staging.git') in c.cd.mock_calls
        assert call('hooks') in c.cd.mock_calls

        c.run.assert_has_calls([
            call('mkdir proj-staging.git'),
            call('git init --bare'),
        ])

        c.put.assert_called_once_with('./post-receive', './', use_sudo=False)
            
    def test_run1(self, c):

        run_app('proj')
        c.cd.assert_called_once_with('/home/www/proj')
        c.sudo.assert_called_once_with('supervisorctl start proj')

    def test_run2(self, c):

        run_app('proj', 'staging')
        c.cd.assert_called_once_with('/home/www/proj-staging')
        c.sudo.assert_called_once_with('supervisorctl start proj-staging')

    def test_stop1(self, c):

        stop_app('proj')
        c.cd.assert_called_once_with('/home/www/proj')
        c.sudo.assert_called_once_with('supervisorctl stop proj')

    def test_stop2(self, c):

        stop_app('proj', 'staging')
        c.cd.assert_called_once_with('/home/www/proj-staging')
        c.sudo.assert_called_once_with('supervisorctl stop proj-staging')

    def test_roolback1(self, c):

        rollback('proj')

        c.lcd.assert_called_once_with('./proj')
        c.local.assert_has_calls([
            call('git revert master --no-edit'),
            call('git push production master')
        ])
        c.sudo.assert_called_once_with('supervisorctl restart proj')

    def test_roolback2(self, c):

        rollback('proj', 'staging')

        c.lcd.assert_called_once_with('./proj')
        c.local.assert_has_calls([
            call('git revert master --no-edit'),
            call('git push staging master')
        ])
        c.sudo.assert_called_once_with('supervisorctl restart proj-staging')

    def test_status(self, c):
        status()
        c.sudo.assert_called_once_with('supervisorctl status')

    def test_create1(self, c):
        create('proj')
        #c.sudo.assert_has_calls(call('apt-get update'))
        assert call('apt-get update') in c.sudo.mock_calls

    def test_create2(self, c):
        create('proj', 'staging')
        #c.sudo.assert_has_calls(call('apt-get update'))
        assert call('apt-get update') in c.sudo.mock_calls

    def test_clean1(self, c):

        clean('proj')

        c.sudo.assert_has_calls([
            call('supervisorctl stop proj'),
            call('rm -rf /home/www/proj'),
            call('rm -rf /home/git/proj'),
            call('rm -f /etc/supervisor/conf.d/proj.conf'),
            call('rm -f /etc/nginx/sites-available/proj'),
            call('rm -f /etc/nginx/sites-enabled/proj'),
        ])

    def test_clean2(self, c):

        clean('proj', 'staging')

        c.sudo.assert_has_calls([
            call('supervisorctl stop proj-staging'),
            call('rm -rf /home/www/proj-staging'),
            call('rm -rf /home/git/proj-staging'),
            call('rm -f /etc/supervisor/conf.d/proj-staging.conf'),
            call('rm -f /etc/nginx/sites-available/proj-staging'),
            call('rm -f /etc/nginx/sites-enabled/proj-staging'),
        ])
    
