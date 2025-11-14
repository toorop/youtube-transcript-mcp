from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import subprocess
import os
import json
import re
from functools import wraps
from webvtt import WebVTT

app = Flask(__name__)
CORS(app)

# Load API keys from file
with open('api_keys.json', 'r') as f:
    API_KEYS = json.load(f)['keys']

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)
        if os.environ.get('AUTH_ENABLED', 'true').lower() == 'true':
            api_key = request.headers.get('X-API-KEY')
            if api_key not in API_KEYS:
                return jsonify({'error': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

def extract_video_id(url):
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def vtt_to_json(vtt_file):
    captions = []
    vtt = WebVTT.read(vtt_file)
    for caption in vtt:
        captions.append({
            'start': caption.start,
            'end': caption.end,
            'text': caption.text
        })
    return captions

@app.route('/test_transcript')
@require_api_key
def test_get_transcript():
    video_id = request.args.get('videoId')
    if not video_id:
        return jsonify({'error': 'Missing videoId parameter'}), 400

    lang = request.args.get('lang', 'en')

    try:
        # Use yt-dlp to download the transcript
        result = subprocess.run(
            [
                'yt-dlp',
                '--extractor-args', 'youtube:player_client=default',
                '--write-auto-sub',
                '--skip-download',
                '--sub-lang',
                lang,
                f'https://www.youtube.com/watch?v={video_id}',
                '-o',
                f'{video_id}.%(ext)s'
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return jsonify({'error': 'Failed to fetch transcript', 'details': result.stderr}), 500

        # Find the downloaded transcript file
        transcript_file = None
        for file in os.listdir('.'):
            if file.startswith(video_id) and file.endswith('.vtt'):
                transcript_file = file
                break
        
        if not transcript_file:
            return jsonify({'error': 'Transcript file not found'}), 500

        # Parse the transcript file
        transcript_json = vtt_to_json(transcript_file)

        # Delete the transcript file
        os.remove(transcript_file)

        return jsonify({'success': True, 'transcript': transcript_json})

    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred', 'details': str(e)}), 500

@app.route('/', methods=['POST', 'OPTIONS'])
@require_api_key
def mcp_handler():
    if request.method == 'OPTIONS':
        return jsonify({'status': 'ok'})

    message = request.get_json()

    if message['method'] == 'initialize':
        response = {
            'jsonrpc': '2.0',
            'id': message['id'],
            'result': {
                'protocolVersion': '2025-03-26',
                'capabilities': {'tools': {}},
                'serverInfo': {
                    'name': 'youtube-transcript-custom',
                    'version': '1.0.0'
                }
            }
        }
        return jsonify(response)

    elif message['method'] == 'tools/list':
        response = {
            'jsonrpc': '2.0',
            'id': message['id'],
            'result': {
                'tools': [{
                    'name': 'get_transcript',
                    'description': 'Extract transcript from YouTube video URL',
                    'inputSchema': {
                        'type': 'object',
                        'properties': {
                            'url': {
                                'type': 'string',
                                'description': 'YouTube video URL (any format)'
                            },
                            'language': {
                                'type': 'string',
                                'description': 'Optional language code (e.g., "en", "fr"). Defaults to "en".'
                            }
                        },
                        'required': ['url']
                    }
                }]
            }
        }
        return jsonify(response)

    elif message['method'] == 'tools/call':
        params = message.get('params', {})
        raw_args = params.get('arguments', {})

        # arguments peut être soit un dict, soit une string JSON
        if isinstance(raw_args, str):
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = {}
        else:
            args = raw_args or {}

        video_url = args.get('url')
        lang = args.get('language', 'en')

        if not video_url:
            response = {
                'jsonrpc': '2.0',
                'id': message['id'],
                'error': {
                    'code': -1,
                    'message': 'Missing or invalid url in arguments'
                }
            }
            return jsonify(response)

        video_id = extract_video_id(video_url)
        if not video_id:
            response = {
                'jsonrpc': '2.0',
                'id': message['id'],
                'error': {
                    'code': -1,
                    'message': 'Invalid YouTube URL'
                }
            }
            return jsonify(response)

        try:
            # Use yt-dlp to download the transcript
            result = subprocess.run(
                [
                    'yt-dlp',
                    '--extractor-args', 'youtube:player_client=default',
                    '--write-auto-sub',
                    '--skip-download',
                    '--sub-lang',
                    lang,
                    f'https://www.youtube.com/watch?v={video_id}',
                    '-o',
                    f'{video_id}.%(ext)s'
                ],
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                response = {
                    'jsonrpc': '2.0',
                    'id': message['id'],
                    'error': {
                        'code': -1,
                        'message': result.stderr
                    }
                }
                return jsonify(response)

            # Find the downloaded transcript file
            transcript_file = None
            for file in os.listdir('.'):
                if file.startswith(video_id) and file.endswith('.vtt'):
                    transcript_file = file
                    break
            
            if not transcript_file:
                response = {
                    'jsonrpc': '2.0',
                    'id': message['id'],
                    'error': {
                        'code': -1,
                        'message': 'Transcript file not found'
                    }
                }
                return jsonify(response)

            # Parse the transcript file
            transcript_json = vtt_to_json(transcript_file)

            # Delete the transcript file
            os.remove(transcript_file)

            payload = {
                "transcript": transcript_json  # <- objet, pas le tableau nu
            }

            response = {
                "jsonrpc": "2.0",
                "id": message["id"],
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(payload, ensure_ascii=False)
                        }
                    ],
                    "structuredContent": payload
                }
            }
            return jsonify(response)


        except Exception as e:
            response = {
                'jsonrpc': '2.0',
                'id': message['id'],
                'error': {
                    'code': -1,
                    'message': str(e)
                }
            }
            return jsonify(response)

    # Fallback for unknown methods
    response = {
        'jsonrpc': '2.0',
        'id': message.get('id'),
        'error': {
            'code': -32601,
            'message': 'Method not found'
        }
    }
    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
