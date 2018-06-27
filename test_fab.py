import unittest
try:
    from unittest.mock import patch, call, mock_open
except ImportError:
    from mock import patch, call, mock_open

from fabfile import *

@patch('fabfile.exists')
@patch('fabfile.sudo')
@patch('fabfile.local')
@patch('fabfile.run')
@patch('fabfile.lcd')
@patch('fabfile.cd')
@patch('fabfile.put')
class TestFab(unittest.TestCase):

        
    def test_install_www(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks
        exists.return_value = False
        install_www()
        sudo.assert_has_calls(
            [call('mkdir /home/www'), call('chown olav:olav /home/www')]
        )

    def test_install_flask1(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks
        exists.return_value = False

        install_flask('proj')

        lcd.assert_called_once_with('./proj')
        cd.assert_called_with('/home/www/proj')
        run.assert_has_calls([
            call('mkdir -p /home/www/proj/proj'),
            call('virtualenv venv3 -p python3'),
            call('source venv3/bin/activate'),
            call('pip install Flask==0.10.1'),
        ])
        put.assert_called_once_with('*', './proj', use_sudo=False)

    def test_install_flask2(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks
        exists.return_value = False

        install_flask('proj', 'staging')

        lcd.assert_called_once_with('./proj')
        cd.assert_called_with('/home/www/proj-staging')
        run.assert_has_calls([
            call('mkdir -p /home/www/proj-staging/proj'),
            call('virtualenv venv3 -p python3'),
            call('source venv3/bin/activate'),
            call('pip install Flask==0.10.1'),
        ])
        put.assert_called_once_with('*', './proj', use_sudo=False)


    def test_confname(self, *mocks):
        assert conf_name('proj') == 'proj'
        assert conf_name('proj', 'staging') == 'proj-staging'

    def test_configure_supervisor(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks

        exists.return_value = True
        configure_supervisor('proj')
        sudo.assert_not_called()
        lcd.assert_not_called()
        cd.assert_not_called()
        put.assert_not_called()

        exists.return_value = False
        configure_supervisor('proj')
        lcd.assert_called_once_with('./config/production')
        cd.assert_called_once_with('/etc/supervisor/conf.d')
        put.assert_called_with('proj.conf', './', use_sudo=True)
        sudo.assert_called_with('supervisorctl reread && supervisorctl update')

    def test_configure_supervisor2(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks

        exists.return_value = True
        configure_supervisor('proj', 'staging')
        sudo.assert_not_called()
        lcd.assert_not_called()
        cd.assert_not_called()
        put.assert_not_called()

        exists.return_value = False
        configure_supervisor('proj', 'staging')
        lcd.assert_called_once_with('./config/staging')
        cd.assert_called_once_with('/etc/supervisor/conf.d')
        put.assert_called_with('proj-staging.conf', './', use_sudo=True)
        sudo.assert_called_with('supervisorctl reread && supervisorctl update')

    def test_configure_git1(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks

        exists.return_value = True
        configure_git('proj')
        sudo.assert_not_called()
        cd.assert_not_called()
        lcd.assert_not_called()
        run.assert_not_called()
        
        exists.return_value = False
        m = mock_open()
        with patch('__builtin__.open', m):
            configure_git('proj')
        m.assert_called_once_with('./config/production/post-receive', 'w')
        m().write.assert_called_once_with(
            '#!/bin/sh\nGIT_WORK_TREE=/home/www/proj git checkout -f\n'
        )

        sudo.assert_has_calls([
            call('mkdir /home/git'),
            call('chown olav:olav /home/git'),
            call('chmod +x post-receive')
        ])
        lcd.assert_called_once_with('./config/production')
        #cd.assert_has_calls([ fails???
        #    call('/home/git'),
        #    call('proj.git'),
        #    call('hooks'),
        #])
        assert call('/home/git') in cd.mock_calls
        assert call('proj.git') in cd.mock_calls
        assert call('hooks') in cd.mock_calls

        #run.assert_has_calls([
        #    call('mkdir proj.git'),
        #    call('git init --bare'),
        #])

        put.assert_called_once_with('./post-receive', './', use_sudo=False)

    def test_configure_git2(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks

        exists.return_value = True
        configure_git('proj', 'staging')
        sudo.assert_not_called()
        cd.assert_not_called()
        lcd.assert_not_called()
        run.assert_not_called()
        
        exists.return_value = False
        
        m = mock_open()
        with patch('__builtin__.open', m):
            configure_git('proj', 'staging')
        m.assert_called_once_with('./config/staging/post-receive', 'w')
        m().write.assert_called_once_with(
            '#!/bin/sh\nGIT_WORK_TREE=/home/www/proj-staging git checkout -f\n'
        )
        
        sudo.assert_has_calls([
            call('mkdir /home/git'),
            call('chown olav:olav /home/git'),
            call('chmod +x post-receive')
        ])
        lcd.assert_called_once_with('./config/staging')

        assert call('/home/git') in cd.mock_calls
        assert call('proj.git') in cd.mock_calls
        assert call('hooks') in cd.mock_calls

        run.assert_has_calls([
            call('mkdir proj.git'),
            call('git init --bare'),
        ])

        put.assert_called_once_with('./post-receive', './', use_sudo=False)
            
    def test_run1(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks

        run_app('proj')
        cd.assert_called_once_with('/home/www/proj')
        sudo.assert_called_once_with('supervisorctl start proj')

    def test_run2(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks

        run_app('proj', 'staging')
        cd.assert_called_once_with('/home/www/proj-staging')
        sudo.assert_called_once_with('supervisorctl start proj-staging')

    def test_stop1(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks

        stop_app('proj')
        cd.assert_called_once_with('/home/www/proj')
        sudo.assert_called_once_with('supervisorctl stop proj')

    def test_stop2(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks

        stop_app('proj', 'staging')
        cd.assert_called_once_with('/home/www/proj-staging')
        sudo.assert_called_once_with('supervisorctl stop proj-staging')

    def test_roolback1(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks

        rollback('proj')

        lcd.assert_called_once_with('./proj')
        local.assert_has_calls([
            call('git revert master --no-edit'),
            call('git push production master')
        ])
        sudo.assert_called_once_with('supervisorctl restart proj')

    def test_roolback2(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks

        rollback('proj', 'staging')

        lcd.assert_called_once_with('./proj')
        local.assert_has_calls([
            call('git revert master --no-edit'),
            call('git push staging master')
        ])
        sudo.assert_called_once_with('supervisorctl restart proj-staging')

    def test_status(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks
        status()
        sudo.assert_called_once_with('supervisorctl status')

    def test_create1(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks
        create('proj')
        sudo.assert_has_calls(call('apt-get update'))

    def test_create2(self, *mocks):
        put, cd, lcd, run, local, sudo, exists = mocks
        create('proj', 'staging')
        sudo.assert_has_calls(call('apt-get update'))
    
