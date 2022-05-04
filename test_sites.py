from unittest.mock import patch, mock_open, MagicMock

import fabfile
import pytest
import textwrap


@pytest.fixture
def c():
    return MagicMock()


@pytest.fixture(params=[8000, 8001])
def port(request):
    return request.param


@patch('fabfile.DEPLOY_ROOT', '/www')
@patch('invoke.tasks.isinstance')  # necessary for mocking
def test_site_nginx(c, port):
    m = mock_open()
    with patch('fabfile.open', m, create=True):
        with patch('fabfile.os.makedirs') as mk:
            fabfile.generate_site_nginx(c, 'foo.bar', port)
    mk.assert_called_once_with('sites/foo.bar/etc/nginx/sites-available')
    m.assert_called_once_with(
        'sites/foo.bar/etc/nginx/sites-available/foo.bar',
        'w'
    )
    m().write.assert_called_with(textwrap.dedent(
        f"""\
        server {{
            server_name foo.bar;
            location / {{
                proxy_pass http://localhost:{port};
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
            }}
            location /static {{
                alias  /www/sites/foo.bar/static/;
            }}
        }}
        """
    ))


@patch('fabfile.DEPLOY_ROOT', '/www')
@patch('fabfile.DEPLOY_USER', 'www')
@patch('invoke.tasks.isinstance')  # necessary for mocking
def test_site_supervisor(c, port):
    m = mock_open()
    with patch('fabfile.open', m, create=True):
        with patch('fabfile.os.makedirs') as mk:
            fabfile.generate_site_supervisor(c, 'foo.bar', 'baz', 'bla', port)
    mk.assert_called_once_with('sites/foo.bar/etc/supervisor/conf.d')
    m.assert_called_once_with(
        'sites/foo.bar/etc/supervisor/conf.d/foo.bar.conf',
        'w'
    )
    m().write.assert_called_with(textwrap.dedent(
        f"""\
        [program:foo.bar]
        command = /www/sites/foo.bar/venv3/bin/gunicorn baz:bla -b localhost:{port}
        directory = /www/sites/foo.bar/src
        user = www
        """
    ))
