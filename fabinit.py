import site
import subprocess

import click
@click.group
def fabinit():
    pass

@fabinit.command('links')
def links():
    install_dir = site.getsitepackages()[0]
    cmd = f'ln -s {install_dir}/fabfile.py .'
    print(cmd)
    subprocess.run(cmd.split())
    cmd = f'ln -s {install_dir}/template.py .'
    print(cmd)
    subprocess.run(cmd.split())
