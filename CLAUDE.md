# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a YouTube transcript extraction service that runs as an MCP (Model Context Protocol) server using FastMCP and Starlette. It uses `yt-dlp` to fetch video transcripts and exposes them via:
- **SSE (Server-Sent Events)** endpoints for Claude Desktop integration
- **Legacy JSON-RPC 2.0** endpoints for n8n and other HTTP clients

The service is containerized with Docker for easy deployment.

## Architecture

### Core Components

**server.py**: Single-file Starlette/FastMCP application implementing:
- **SSE endpoints** (`/sse/*`) for Claude Desktop via mcp-remote
- **Legacy MCP handler** (`/` POST) with JSON-RPC 2.0 for n8n
- **Test endpoint** (`/test_transcript` GET) for direct transcript fetching
- API key authentication via `X-API-KEY` header (legacy endpoints only)
- VTT to JSON transcript conversion
- FastMCP `@mcp.tool()` decorator for tool registration

**Authentication Flow**:
- API keys loaded from `api_keys.json` at startup
- `@require_api_key` decorator protects legacy HTTP endpoints (`/`, `/test_transcript`)
- SSE endpoints (`/sse`) are NOT protected by the decorator (use reverse proxy for auth)
- Can be disabled via `AUTH_ENABLED=false` environment variable (useful when using reverse proxy for all endpoints)
- OPTIONS requests bypass authentication for CORS preflight

**Transcript Extraction Process**:
1. Extract video ID from URL using regex patterns (supports multiple YouTube URL formats)
2. Execute `yt-dlp` subprocess with `--write-auto-sub --skip-download` flags
3. Parse generated `.vtt` file using `webvtt-py` library
4. Convert to JSON structure with `start`, `end`, `text` fields
5. Clean up temporary `.vtt` file

### MCP Protocol Implementation

The server implements two transport modes:

**1. SSE Transport (Claude Desktop)**:
- Mounted at `/sse` via `mcp.sse_app()`
- Handles bidirectional JSON-RPC 2.0 over SSE
- Tool defined with `@mcp.tool()` decorator (server.py:91-112)
- No authentication required (use Caddy/reverse proxy for auth)

**2. Legacy JSON-RPC Transport (n8n)**:
- Available at `/` endpoint (POST)
- Implements three MCP methods:
  - `initialize`: Returns server capabilities and protocol version
  - `tools/list`: Advertises the `get_transcript` tool with schema
  - `tools/call`: Executes transcript extraction
- Arguments can be passed as either JSON string or object (server.py:196-202)
- Protected by API key authentication

## Development Commands

### Build and Run

```bash
# Build and start the Docker container
docker-compose up -d --build

# View logs
docker logs <container-name>

# Stop the container
docker-compose down
```

### Testing

```bash
# Test transcript endpoint (replace with your API key and video ID)
curl -H "X-API-KEY: your-api-key" "http://localhost:5000/test_transcript?videoId=VIDEO_ID"

# Test MCP endpoint
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_transcript","arguments":{"url":"https://www.youtube.com/watch?v=VIDEO_ID"}}}' \
  http://localhost:5000/
```

### Local Development (without Docker)

```bash
# Install Python dependencies
pip install fastmcp webvtt-py uvicorn starlette

# Install yt-dlp
wget https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -O /usr/local/bin/yt-dlp
chmod a+rx /usr/local/bin/yt-dlp

# Run the server
python server.py
# or with uvicorn
uvicorn server:app --host 0.0.0.0 --port 5000
```

## Configuration

**api_keys.json**: Contains array of valid API keys
```json
{
  "keys": ["your-api-key-here"]
}
```

**docker-compose.yml**:
- `AUTH_ENABLED`: Set to `false` to disable authentication (default: `true`)
- Port mapping: 5000:5000

**yt-dlp flags**:
- `--extractor-args youtube:player_client=default`: Ensures compatibility with YouTube
- `--write-auto-sub`: Downloads auto-generated subtitles
- `--skip-download`: Only fetches transcript, not video
- `--sub-lang`: Language code (e.g., "en", "fr")

## Claude Desktop Configuration

To connect Claude Desktop to your remote server, use `mcp-remote` as an adapter:

```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://your-domain.com/sse"
      ]
    }
  }
}
```

**Note**: Replace `https://your-domain.com` with your actual server URL behind Caddy.

## n8n Configuration

For n8n workflows, use the legacy HTTP endpoints:

**Initialize connection:**
```
POST https://your-domain.com/
Headers: X-API-KEY: your-api-key
Body: {"jsonrpc":"2.0","id":1,"method":"initialize"}
```

**Get transcript:**
```
POST https://your-domain.com/
Headers: X-API-KEY: your-api-key
Body: {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_transcript","arguments":{"url":"VIDEO_URL","language":"en"}}}
```

## Authentication Strategies

The server supports two authentication approaches:

**Strategy 1: Hybrid Authentication (default, `AUTH_ENABLED=true`)**
- SSE endpoints (`/sse`): Protected by reverse proxy (Caddy with Basic Auth, API Key, or IP whitelist)
- Legacy HTTP endpoints (`/`, `/test_transcript`): Protected by server with `X-API-KEY` header
- Use case: Different clients with different auth methods (e.g., Claude Desktop uses Caddy auth, n8n uses X-API-KEY)

**Strategy 2: Reverse Proxy Only (`AUTH_ENABLED=false`)**
- ALL endpoints protected by reverse proxy (Caddy with Basic Auth or API Key header)
- Server-level authentication completely disabled
- Use case: Centralized authentication, single auth mechanism, simplified configuration

**When to use each:**
- Use Strategy 1 if you want flexibility (some clients use Basic Auth, others use API keys)
- Use Strategy 2 if you want simplicity (all authentication handled by Caddy, no need for `api_keys.json`)

## Important Notes

- The server processes one transcript request at a time (synchronous subprocess calls)
- Temporary `.vtt` files are created in the working directory and deleted after parsing
- Video ID extraction supports: `youtube.com/watch?v=`, `youtu.be/`, `youtube.com/embed/`, and raw 11-character IDs
- The MCP `tools/call` response includes both `content` (JSON string) and `structuredContent` (JSON object) fields
