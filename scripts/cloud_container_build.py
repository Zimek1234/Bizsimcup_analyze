"""Cloud workspace only: keep TLS verification, mount its trusted CA bundle, resolve its proxy."""
import os
from pathlib import Path
import socket
import ssl
import subprocess
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
args=['docker','build','--network=host']
seen=set()
for key in ['HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy']:
    if not os.environ.get(key):continue
    args+=['--build-arg',key]
    host=urlsplit(os.environ[key]).hostname
    if host and host not in seen:
        seen.add(host)
        ip=socket.getaddrinfo(host,None,socket.AF_INET)[0][4][0]
        args+=['--add-host',host+':'+ip]
ca=ssl.get_default_verify_paths().cafile
if ca and Path(ca).is_file():args+=['--secret','id=build_ca,src='+ca]
args+=['-f','deployment/Dockerfile.sync','-t','erpsim-sync:local','.']
cache=Path('/workspace/.cache/docker');cache.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,DOCKER_CONFIG=str(cache))
# Log stays outside repo; never print proxy credential values.
with open('/tmp/erpsim-sync-build.log','w') as log:
    result=subprocess.run(args,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
print('Container build exit status:',result.returncode)
raise SystemExit(result.returncode)
