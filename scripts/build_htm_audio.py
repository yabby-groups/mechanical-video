"""Build the pinned, tracked htm.core source in a new isolated directory.

Run with the project's .venv/bin/python. Never writes into the source checkout.
Build products/venv/third-party source are intentionally not repository assets.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import io

REVISION = '0cab77fa638925e0c84a1b2aa6c7cc1258cb66f1'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def tree_hash(directory):
    value = hashlib.sha256()
    for p in sorted(Path(directory).rglob('*')):
        if p.is_file() and '.git' not in p.parts:
            value.update(str(p.relative_to(directory)).encode()+b'\0'+bytes.fromhex(digest(p)))
    return value.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True)
    p.add_argument('--work', required=True)
    p.add_argument('--thirdparty-lock', help='Expected dependency tree hash JSON from a verified prior build')
    a = p.parse_args()
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=False)
    source = work/'source'
    source.mkdir()
    archive = subprocess.check_output(['git', '-C', a.source, 'archive', REVISION])
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        # Fixed trusted git revision, not an arbitrary supplied tarball.
        stream.extractall(source, filter='data')
    env = {**os.environ, 'UV_CACHE_DIR': str(work/'uv-cache'), 'CMAKE_BUILD_PARALLEL_LEVEL': '4'}
    python = work/'venv/bin/python'
    commands = [
        ['uv', 'venv', '--python', sys.executable, str(work/'venv')],
        ['cmake', '-S', str(source), '-B', str(source/'build/Release'),
         '-DBINDING_BUILD=CPP_Only', '-DCMAKE_BUILD_TYPE=Release',
         '-DCMAKE_INSTALL_PREFIX='+str(source/'build/Release'), '-DCMAKE_POLICY_VERSION_MINIMUM=3.5'],
        ['cmake', '--build', str(source/'build/Release'), '--target', 'install', '-j', '4'],
        ['uv', 'pip', 'install', '--python', str(python), str(source)],
    ]
    with (work/'build.log').open('w') as log:
        for command in commands:
            log.write(json.dumps(command)+'\n'); log.flush()
            subprocess.run(command, check=True, env=env, stdout=log, stderr=subprocess.STDOUT)
    deps = source/'build/Release'
    dependency_hashes = {d.name: tree_hash(d) for d in sorted(list(deps.glob('*-src'))+list((deps/'_deps').glob('*-src')))}
    if a.thirdparty_lock and dependency_hashes != json.loads(Path(a.thirdparty_lock).read_text()):
        raise ValueError('third-party sources drifted; build cannot be used')
    (work/'thirdparty-lock.json').write_text(json.dumps(dependency_hashes, indent=2)+'\n')
    probe = """import json,sys,htm.bindings.algorithms as a,htm.bindings.sdr as s
print(json.dumps({'python':sys.version,'bindings':[a.__file__,s.__file__]}))"""
    observed = json.loads(subprocess.check_output([str(python), '-c', probe]))
    result = {'source_revision': REVISION, 'source_archive_sha256': hashlib.sha256(archive).hexdigest(),
              'platform': platform.platform(), 'python': observed['python'],
              'commands': commands, 'thirdparty': dependency_hashes,
              'bindings': [{'path': f, 'sha256': digest(f)} for f in observed['bindings']],
              'build_log_sha256': digest(work/'build.log'),
              'toolchain': {tool: subprocess.check_output([tool, '--version'], text=True).splitlines()[0]
                            for tool in ('cmake', 'c++', 'uv')}}
    (work/'build-manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    print(work/'build-manifest.json')


if __name__ == '__main__':
    main()
