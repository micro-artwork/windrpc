import subprocess
from pathlib import Path

current_dir = Path(__file__).resolve().parent
gen_script = current_dir / '../../windrpc/windrpc_gen.py'
user_spec_file = current_dir / 'user_spec.yml'
protos_dir = current_dir / 'protos'
server_dir = current_dir / 'server'

# create proto files
subprocess.run([
    'python',
    gen_script,
    'proto',
    '-s',
    user_spec_file,
    '-o',
    protos_dir
], check=True)

# create server files
subprocess.run([
    'python',
    gen_script,
    'server',
    '-s',
    user_spec_file,
    '-o',
    server_dir
], check=True)
