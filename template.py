from string import Template
NGINX = """\
server {{
    server_name {server_name};
    location / {{
        proxy_pass http://localhost:{port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}
    location /static {{
        alias  {root}/sites/{server_name}/static/;
    }}
}}
"""

SUPERVISOR = {}

SUPERVISOR["flask"] = """\
[program:{program}]
command = {bin}/gunicorn {module}:{app} -b localhost:{port}
directory = {src}
user = {user}
"""

SUPERVISOR["fastapi"] = """\
[program:{program}]
command = {bin}/uvicorn {module}:{app} --port {port}
directory = {src}
user = {user}
"""

