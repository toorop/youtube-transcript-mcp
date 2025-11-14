# YouTube Transcript MCP Server

A powerful MCP (Model Context Protocol) server that fetches YouTube video transcripts using `yt-dlp`, with dual transport support for both Claude Desktop and HTTP clients.

## Features

- ✅ **Reliable**: Uses `yt-dlp` to fetch transcripts, which is regularly updated to handle YouTube's changes
- ✅ **Containerized**: Runs in a Docker container for easy deployment and portability
- ✅ **Dual Transport**: Supports SSE (Server-Sent Events) for Claude Desktop AND JSON-RPC for HTTP clients
- ✅ **MCP Compliant**: Implements the Model Context Protocol for seamless AI tool integration
- ✅ **Multi-language Support**: Fetch transcripts in any available language (English, French, Spanish, etc.)
- ✅ **Secure**: Optional API key authentication for HTTP endpoints

---

## Table of Contents

- [Quick Start](#quick-start)
- [Docker Deployment](#docker-deployment)
- [Claude Desktop Integration](#claude-desktop-integration)
- [n8n Integration](#n8n-integration)
- [API Reference](#api-reference)
- [Configuration](#configuration)

---

## Quick Start

### Prerequisites

- [Docker](https://www.docker.com/) installed
- [Docker Compose](https://docs.docker.com/compose/) installed
- (Optional) [Node.js](https://nodejs.org/) for Claude Desktop integration

### Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd youtube-transcript-mcp
   ```

2. **Configure API keys:**

   Create a file named `api_keys.json` in the root directory:
   ```json
   {
     "keys": [
       "your-super-secret-api-key-here"
     ]
   }
   ```

3. **Build and run:**
   ```bash
   docker-compose up -d --build
   ```

4. **Verify the server is running:**
   ```bash
   curl http://localhost:5000/test_transcript?videoId=dQw4w9WgXcQ
   ```

---

## Docker Deployment

### Build and Run

From the project root directory:

```bash
docker-compose up -d --build
```

The server will be running on `http://localhost:5000`.

### Environment Variables

Edit `docker-compose.yml` to configure:

- `AUTH_ENABLED`: Set to `false` to disable API key authentication (default: `true`)

### View Logs

```bash
docker logs <container-name>
```

### Stop the Server

```bash
docker-compose down
```

---

---

## API Reference

The server exposes multiple endpoints supporting different transport protocols:

### Endpoints Overview

| Endpoint | Method | Transport | Authentication | Purpose |
|----------|--------|-----------|----------------|---------|
| `/sse` | GET | SSE | None* | Claude Desktop integration |
| `/` | POST | JSON-RPC 2.0 | API Key | n8n and HTTP clients |
| `/test_transcript` | GET | REST | API Key | Quick testing |

*SSE endpoints should be protected by your reverse proxy (e.g., Caddy, Nginx)

### Authentication

- **SSE endpoints** (`/sse`): Not authenticated by default - use your reverse proxy for access control
- **HTTP endpoints** (`/`, `/test_transcript`): Protected with `X-API-KEY` header

To disable authentication for HTTP endpoints, set `AUTH_ENABLED=false` in `docker-compose.yml`.

---

### Endpoint: GET /test_transcript

Simple REST endpoint for testing transcript fetching.

**Parameters:**
- `videoId` (required): YouTube video ID
- `lang` (optional): Language code (default: `en`)

**Example:**
```bash
curl -H "X-API-KEY: your-api-key" \
  "http://localhost:5000/test_transcript?videoId=dQw4w9WgXcQ&lang=en"
```

**Response:**
```json
{
  "success": true,
  "transcript": [
    {
      "start": "00:00:00.000",
      "end": "00:00:02.500",
      "text": "Hello world"
    }
  ]
}
```

---

### Endpoint: POST /

MCP-compliant JSON-RPC 2.0 endpoint for n8n and other HTTP clients.

**Supported Methods:**
- `initialize`: Get server capabilities
- `tools/list`: List available tools
- `tools/call`: Execute the `get_transcript` tool

**Example - Get Transcript:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: your-api-key" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "get_transcript",
      "arguments": {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "language": "en"
      }
    }
  }' \
  http://localhost:5000/
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"transcript\":[{\"start\":\"00:00:00.000\",\"end\":\"00:00:02.500\",\"text\":\"Hello world\"}]}"
      }
    ],
    "structuredContent": {
      "transcript": [
        {
          "start": "00:00:00.000",
          "end": "00:00:02.500",
          "text": "Hello world"
        }
      ]
    }
  }
}
```

**Error Response:**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -1,
    "message": "Invalid YouTube URL"
  }
}
```

---

## Claude Desktop Integration

Claude Desktop connects to MCP servers via SSE (Server-Sent Events) using the `mcp-remote` adapter.

### Setup Instructions

**Step 1: Ensure Node.js is installed**

Claude Desktop uses `npx` to run `mcp-remote`. Verify Node.js installation:
```bash
node --version
```

**Step 2: Configure Claude Desktop**

Add the following to your `claude_desktop_config.json`:

**For macOS:**
```bash
~/Library/Application Support/Claude/claude_desktop_config.json
```

**For Windows:**
```bash
%APPDATA%\Claude\claude_desktop_config.json
```

**Configuration:**

**Option 1: Without authentication (SSE endpoint publicly accessible):**
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

**Option 2: With HTTP Basic Auth (recommended):**
```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://username:password@your-domain.com/sse"
      ]
    }
  }
}
```

**Option 3: With custom headers (API key, Bearer token, etc.):**
```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "--header",
        "Authorization: Bearer your-token-here",
        "https://your-domain.com/sse"
      ]
    }
  }
}
```

**Important:** Replace `https://your-domain.com` with your actual server URL (e.g., behind Caddy or Nginx).

**Step 3: Restart Claude Desktop**

After saving the configuration, completely restart Claude Desktop.

**Step 4: Verify**

In a new conversation, the `get_transcript` tool should now be available. Test it by asking:
> "Can you fetch the transcript from this YouTube video: https://www.youtube.com/watch?v=dQw4w9WgXcQ"

### Securing the SSE Endpoint

Since SSE endpoints are not authenticated by default, protect them with your reverse proxy.

#### Example 1: Caddy with Basic Auth

**Generate password hash:**
```bash
caddy hash-password
```

**Caddyfile:**
```caddy
your-domain.com {
    reverse_proxy /sse/* localhost:5000

    # Add basic authentication
    basicauth /sse/* {
        alice $2a$14$hashed_password_here
    }
}
```

**Claude Desktop configuration:**
```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://alice:your-password@your-domain.com/sse"
      ]
    }
  }
}
```

#### Example 2: Caddy with API Key Header

**Caddyfile:**
```caddy
your-domain.com {
    @sse_auth {
        path /sse/*
        header X-API-Key "your-secret-api-key"
    }

    handle @sse_auth {
        reverse_proxy localhost:5000
    }

    # Reject requests without valid API key
    handle /sse/* {
        respond "Unauthorized" 401
    }

    # Allow other paths without auth (or add separate rules)
    reverse_proxy localhost:5000
}
```

**Claude Desktop configuration:**
```json
{
  "mcpServers": {
    "youtube-transcript": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "--header",
        "X-API-Key: your-secret-api-key",
        "https://your-domain.com/sse"
      ]
    }
  }
}
```

#### Example 3: IP Whitelist (no credentials needed)

**Caddyfile:**
```caddy
your-domain.com {
    @sse_trusted {
        path /sse/*
        remote_ip 192.168.1.0/24 10.0.0.0/8
    }

    handle @sse_trusted {
        reverse_proxy localhost:5000
    }

    handle /sse/* {
        respond "Forbidden" 403
    }

    reverse_proxy localhost:5000
}
```

**Claude Desktop configuration:**
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

---

## n8n Integration

Integrate this MCP server into your n8n workflows using the HTTP Request node.

### HTTP Request Node Setup

1. **Add an HTTP Request node** to your workflow

2. **Configure the node:**

   - **Method**: `POST`
   - **URL**: `https://your-domain.com/`
   - **Authentication**: None (use headers for API key)

3. **Add Headers:**

   | Name | Value |
   |------|-------|
   | `Content-Type` | `application/json` |
   | `X-API-KEY` | `your-api-key-here` |

4. **Set Body (JSON):**
   ```json
   {
     "jsonrpc": "2.0",
     "id": 1,
     "method": "tools/call",
     "params": {
       "name": "get_transcript",
       "arguments": {
         "url": "{{ $json.videoUrl }}",
         "language": "en"
       }
     }
   }
   ```

### Example Workflow

**Scenario:** Extract transcript from YouTube URLs submitted via webhook

1. **Webhook Trigger** - Receives YouTube URL
2. **HTTP Request** - Calls this MCP server
3. **Set Node** - Extracts transcript from response
4. **Process Transcript** - Analyze, summarize, or store

### Response Handling

The response will be in the `result.structuredContent.transcript` field:

```javascript
// n8n expression to access transcript
{{ $json.result.structuredContent.transcript }}
```

---

## Configuration

### api_keys.json

Contains valid API keys for HTTP endpoint authentication.

```json
{
  "keys": [
    "production-key-1",
    "production-key-2",
    "development-key"
  ]
}
```

### docker-compose.yml

Configure environment variables:

```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - AUTH_ENABLED=false  # Set to 'false' to disable authentication
```

### Supported Languages

You can fetch transcripts in any language supported by YouTube. Common codes:

- `en` - English
- `fr` - French
- `es` - Spanish
- `de` - German
- `ja` - Japanese
- `ko` - Korean
- `zh` - Chinese
- `ar` - Arabic

**Example:**
```bash
curl -H "X-API-KEY: your-key" \
  "http://localhost:5000/test_transcript?videoId=dQw4w9WgXcQ&lang=fr"
```

---

## Troubleshooting

### Docker Container Won't Start

**Check logs:**
```bash
docker logs <container-name>
```

**Common issues:**
- Missing `api_keys.json` file
- Port 5000 already in use
- Invalid Docker configuration

### Claude Desktop Can't Connect

**Verify:**
1. Server is accessible at the configured URL
2. Node.js and `npx` are available
3. `claude_desktop_config.json` syntax is correct
4. Claude Desktop has been fully restarted

**Test SSE endpoint:**
```bash
curl https://your-domain.com/sse
```

### n8n Returns 401 Unauthorized

**Check:**
1. `X-API-KEY` header is set correctly
2. API key exists in `api_keys.json`
3. `AUTH_ENABLED` is not set to `false`

### Transcript Not Available

**Possible causes:**
- Video has no captions/subtitles
- Requested language not available
- Video is private or restricted
- `yt-dlp` needs updating

**Solution:** Try with `lang=en` (auto-generated English subtitles are most common)

---

## License

This project is open source and available under the MIT License.

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) - Python MCP SDK
- Uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) for reliable transcript extraction
- Implements the [Model Context Protocol](https://modelcontextprotocol.io/)
