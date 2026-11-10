"""Fetch a pinned, licensed AISHELL-1 subset for local HTM acoustic experiments.

Downloads approximately 170 MB. Existing evidence is preserved and verified.
This corpus has transcripts but no independent naturalness/expression ratings.
"""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

REVISION = 'bbe295d530192a4cd41644b711c9aecd087df653'
REPOSITORY = 'AISHELL/AISHELL-1'
LICENSE_URL = 'https://www.openslr.org/33/'


def request(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={
        'User-Agent': 'mechanical-video-audio-validation'}), timeout=90)


def fetch(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    metadata_path = root/'upstream-metadata.json'
    if not metadata_path.exists():
        with request('https://huggingface.co/api/datasets/'+REPOSITORY+'/revision/'+REVISION+'?blobs=true') as response:
            metadata_path.write_bytes(response.read())
    metadata = json.loads(metadata_path.read_text())
    if metadata['sha'] != REVISION:
        raise ValueError('upstream revision mismatch')
    license_path = root/'upstream-license.html'
    if not license_path.exists():
        with request(LICENSE_URL) as response:
            license_path.write_bytes(response.read())
    if b'Apache License v.2.0' not in license_path.read_bytes():
        raise ValueError('official license evidence unavailable')
    paths = ['data_aishell/transcript/aishell_transcript_v0.8.txt'] + [
        'data_aishell/wav/S%04d.tar.gz'%n for n in range(2, 7)]
    base = 'https://huggingface.co/datasets/'+REPOSITORY+'/resolve/'+REVISION+'/'

    def one(path):
        entry = next(e for e in metadata['siblings'] if e['rfilename'] == path)
        target = root/Path(path).name
        if not target.exists():
            partial = target.with_suffix(target.suffix+'.partial')
            with request(base+path) as response, partial.open('xb') as output:
                while True:
                    chunk = response.read(1024*1024)
                    if not chunk:
                        break
                    output.write(chunk)
            partial.rename(target)
        payload = target.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        if len(payload) != entry['size']:
            raise ValueError('source size mismatch: '+path)
        if entry.get('lfs'):
            if digest != entry['lfs']['sha256']:
                raise ValueError('LFS source hash mismatch: '+path)
        else:
            blob = b'blob '+str(len(payload)).encode()+b'\0'+payload
            if hashlib.sha1(blob).hexdigest() != entry['blobId']:
                raise ValueError('Git source blob mismatch: '+path)
        return dict(path=str(target), sha256=digest, size=len(payload), url=base+path)

    with concurrent.futures.ThreadPoolExecutor(3) as pool:
        files = list(pool.map(one, paths))
    manifest = dict(repository=REPOSITORY, revision=REVISION, license='Apache-2.0',
                    license_source=LICENSE_URL, files=files,
                    scope='research-only local reviewer validation; no publication and no MOS labels')
    target = root/'source-manifest.json'
    if target.exists():
        if json.loads(target.read_text()) != manifest:
            raise ValueError('existing frozen source manifest differs; use a new output directory')
    else:
        with target.open('x') as output:
            json.dump(manifest, output, indent=2)
    print(target)
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    fetch(parser.parse_args().output)
