"""Check EP02 speech text with the configured Qwen ASR endpoint."""
import argparse
import base64
import difflib
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('audio', type=Path)
    parser.add_argument('script', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    marker = args.output.with_suffix('.submitted')
    if args.output.exists() or marker.exists():
        raise RuntimeError('Existing result or uncertain submission; inspect before retrying')
    payload = {'model': 'qwen3-asr-flash', 'input': {'messages': [{'role': 'user', 'content': [
        {'audio': 'data:audio/mpeg;base64,' + base64.b64encode(args.audio.read_bytes()).decode()}]}]},
        'parameters': {'asr_options': {'enable_itn': False, 'language': 'zh'}}}
    request = urllib.request.Request(
        'https://huabot.com/api/dashscope/v1/services/aigc/multimodal-generation/generation',
        data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY'], 'Content-Type': 'application/json'})
    marker.touch(exist_ok=False)
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.load(response)
    transcript = ''.join(item.get('text', '') for item in data['output']['choices'][0]['message']['content'])
    if not transcript.strip():
        raise RuntimeError('Empty transcript; inspect submission before retrying')
    normalize = lambda text: re.sub(r'[^\w\u4e00-\u9fff]', '', text).lower()
    expected = normalize(args.script.read_text())
    actual = normalize(transcript)
    changes = [{'kind': tag, 'expected': expected[i:j], 'actual': actual[k:l]}
               for tag, i, j, k, l in difflib.SequenceMatcher(None, expected, actual).get_opcodes()
               if tag != 'equal']
    result = {'model': 'qwen3-asr-flash', 'audio_sha256': hashlib.sha256(args.audio.read_bytes()).hexdigest(),
              'script_sha256': hashlib.sha256(args.script.read_bytes()).hexdigest(),
              'transcript': transcript, 'normalized_exact_match': not changes, 'differences': changes,
              'scope': 'ASR text comparison; does not assess delivery, timing, or sound quality'}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f'ASR result saved; {len(changes)} normalized differences')


if __name__ == '__main__':
    main()
