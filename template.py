from string import Template
NGINX = """\
server {{
    server_name {server_name};
    location / {{
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
    location /static {{
        alias  {root}/sites/{server_name}/static/;
    }}
}}
"""

SUPERVISOR = """\
[program:{program}]
command = gunicorn {module}:{app} -b localhost:8000
directory = /home/www/sites/{site}/src
user = {user}
"""

