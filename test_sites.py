from unittest.mock import patch, mock_open, MagicMock
import pytest
from fabfile import *

@pytest.fixture
def c():
    return MagicMock()

@patch('fabfile.REMOTE_ROOT', '/www')
@patch('invoke.tasks.isinstance') # necessary for mocking
def test_site_nginx(c):
    m = mock_open()
    with patch('fabfile.open', m, create=True):
        with patch('fabfile.os.makedirs') as mk:
            generate_site_nginx(c, 'foo.bar')
    #c.local.assert_called_once_with(
    #    'mkdir -p sites/foo.bar/etc/nginx/sites-available'
    #)
    mk.assert_called_once_with('sites/foo.bar/etc/nginx/sites-available')
    m.assert_called_once_with(
        'sites/foo.bar/etc/nginx/sites-available/foo.bar',
        'w'
    )
    m().write.assert_called_with(
"""\
server {
    server_name foo.bar;
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    location /static {
        alias  /www/sites/foo.bar/static/;
    }
"""
    )


@patch('fabfile.REMOTE_ROOT', '/www')
@patch('fabfile.user', 'www')
@patch('invoke.tasks.isinstance') # necessary for mocking
def test_site_supervisor(c):
    m = mock_open()
    with patch('fabfile.open', m, create=True):
        with patch('fabfile.os.makedirs') as mk:
            generate_site_supervisor(c, 'foo.bar', 'baz', 'bla')
    mk.assert_called_once_with('sites/foo.bar/etc/supervisor/conf.d')
    m.assert_called_once_with(
        'sites/foo.bar/etc/supervisor/conf.d/foo.bar.conf',
        'w'
    )
    m().write.assert_called_with(
"""\
[program:foo.bar]
command = gunicorn3 baz:bla -b localhost:8000
directory = /home/www/sites/foo.bar/src
user = www
"""
    )
