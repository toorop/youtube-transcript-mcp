import subprocess
import os
import json
import re
import uvicorn
from typing import Any
from webvtt import WebVTT
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

# Initialize FastMCP server
mcp = FastMCP("youtube-transcript-custom")

# Load API keys from file
with open('api_keys.json', 'r') as f:
    API_KEYS = json.load(f)['keys']

def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def vtt_to_json(vtt_file: str) -> list[dict]:
    """Convert VTT transcript file to JSON format"""
    captions = []
    vtt = WebVTT.read(vtt_file)
    for caption in vtt:
        captions.append({
            'start': caption.start,
            'end': caption.end,
            'text': caption.text
        })
    return captions

def fetch_transcript(video_id: str, lang: str = 'en') -> dict:
    """Fetch YouTube transcript using yt-dlp with language fallback"""

    # Define language fallback strategy
    # Try requested language first, then common fallbacks
    if lang == 'en':
        lang_attempts = ['en', 'fr', 'es', 'de', 'pt', 'ja', 'ko']
    elif lang == 'fr':
        lang_attempts = ['fr', 'fr-orig', 'en', 'es', 'de']
    else:
        lang_attempts = [lang, 'en', 'fr', 'es']

    last_error_details = None

    for attempt_lang in lang_attempts:
        try:
            # Clean up any existing VTT files before attempting download
            for file in os.listdir('.'):
                if file.startswith(video_id) and file.endswith('.vtt'):
                    os.remove(file)

            # Use yt-dlp to download the transcript
            result = subprocess.run(
                [
                    'yt-dlp',
                    '--extractor-args', 'youtube:player_client=default',
                    '--write-auto-sub',
                    '--skip-download',
                    '--sub-lang',
                    attempt_lang,
                    f'https://www.youtube.com/watch?v={video_id}',
                    '-o',
                    f'{video_id}.%(ext)s'
                ],
                capture_output=True,
                text=True,
                timeout=30
            )

            # Don't rely on returncode - check if VTT file was created instead
            # yt-dlp may return non-zero even if subtitles were downloaded successfully
            transcript_file = None
            for file in os.listdir('.'):
                if file.startswith(video_id) and file.endswith('.vtt'):
                    transcript_file = file
                    break

            if transcript_file:
                # Success! Parse the transcript file
                transcript_json = vtt_to_json(transcript_file)

                # Extract the actual language from filename (e.g., "videoId.fr.vtt" -> "fr")
                file_parts = transcript_file.split('.')
                actual_lang = file_parts[-2] if len(file_parts) >= 3 else attempt_lang

                # Delete the transcript file
                os.remove(transcript_file)

                return {
                    'success': True,
                    'transcript': transcript_json,
                    'language': actual_lang,
                    'requested_language': lang
                }

            # No file found, save error and continue to next language
            last_error_details = result.stderr if result.stderr else f"No subtitles for '{attempt_lang}'"

        except subprocess.TimeoutExpired:
            last_error_details = f"Timeout fetching subtitles for '{attempt_lang}'"
            continue
        except Exception as e:
            last_error_details = f"Error with '{attempt_lang}': {str(e)}"
            continue

    # All language attempts failed
    return {
        'success': False,
        'error': 'Failed to fetch transcript in any available language',
        'details': last_error_details,
        'attempted_languages': lang_attempts
    }

# MCP Tool: Get Transcript
@mcp.tool()
def get_transcript(url: str, language: str = "en") -> dict[str, Any]:
    """
    Extract transcript from YouTube video URL

    Args:
        url: YouTube video URL (any format) or video ID
        language: Optional language code (e.g., "en", "fr"). Defaults to "en"

    Returns:
        Dictionary containing the transcript with start, end, text fields, and language info
    """
    video_id = extract_video_id(url)
    if not video_id:
        return {'error': 'Invalid YouTube URL'}

    result = fetch_transcript(video_id, language)

    if result['success']:
        return {
            'transcript': result['transcript'],
            'language': result.get('language'),
            'requested_language': result.get('requested_language')
        }
    else:
        return {
            'error': result.get('error', 'Unknown error'),
            'details': result.get('details', ''),
            'attempted_languages': result.get('attempted_languages', [])
        }

# Authentication middleware for legacy endpoints
def require_api_key(func):
    async def wrapper(request: Request):
        if os.environ.get('AUTH_ENABLED', 'true').lower() == 'true':
            api_key = request.headers.get('X-API-KEY')
            if api_key not in API_KEYS:
                return JSONResponse({'error': 'Invalid API key'}, status_code=401)
        return await func(request)
    return wrapper

# Legacy endpoint for n8n: /test_transcript
@require_api_key
async def test_transcript_handler(request: Request):
    """Legacy GET endpoint for testing transcript fetching (n8n compatible)"""
    video_id = request.query_params.get('videoId')
    if not video_id:
        return JSONResponse({'error': 'Missing videoId parameter'}, status_code=400)

    lang = request.query_params.get('lang', 'en')
    result = fetch_transcript(video_id, lang)

    if result['success']:
        return JSONResponse(result)
    else:
        return JSONResponse(result, status_code=500)

# Legacy endpoint for n8n: / (JSON-RPC)
@require_api_key
async def legacy_mcp_handler(request: Request):
    """Legacy JSON-RPC endpoint for n8n compatibility"""
    if request.method == 'OPTIONS':
        return JSONResponse({'status': 'ok'})

    message = await request.json()

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
        return JSONResponse(response)

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
        return JSONResponse(response)

    elif message['method'] == 'tools/call':
        params = message.get('params', {})
        raw_args = params.get('arguments', {})

        # arguments can be either dict or JSON string
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
            return JSONResponse(response)

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
            return JSONResponse(response)

        result = fetch_transcript(video_id, lang)

        if result['success']:
            payload = {
                'transcript': result['transcript'],
                'language': result.get('language'),
                'requested_language': result.get('requested_language')
            }
            response = {
                'jsonrpc': '2.0',
                'id': message['id'],
                'result': {
                    'content': [
                        {
                            'type': 'text',
                            'text': json.dumps(payload, ensure_ascii=False)
                        }
                    ],
                    'structuredContent': payload
                }
            }
            return JSONResponse(response)
        else:
            response = {
                'jsonrpc': '2.0',
                'id': message['id'],
                'error': {
                    'code': -1,
                    'message': result.get('error', 'Unknown error'),
                    'details': result.get('details', ''),
                    'attempted_languages': result.get('attempted_languages', [])
                }
            }
            return JSONResponse(response)

    # Fallback for unknown methods
    response = {
        'jsonrpc': '2.0',
        'id': message.get('id'),
        'error': {
            'code': -32601,
            'message': 'Method not found'
        }
    }
    return JSONResponse(response)

# Create Starlette app with all routes
app = Starlette(
    routes=[
        # 1. D'abord les routes spécifiques (Legacy n8n)
        Route("/test_transcript", test_transcript_handler, methods=["GET"]),
        Route("/", legacy_mcp_handler, methods=["POST", "OPTIONS"]),
        
        # 2. Ensuite le Mount à la racine (Catch-all)
        # Comme il est à la racine "/", il passera "/sse" directement à l'app MCP
        Mount("/", app=mcp.sse_app()),
    ]
)

# Add proxy headers middleware (MUST be added first)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=5000)
