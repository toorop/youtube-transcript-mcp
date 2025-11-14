# YouTube Transcript Server

A simple server to fetch the transcript of a YouTube video using `yt-dlp`.

- ✅ **Reliable**: Uses `yt-dlp` to fetch transcripts, which is regularly updated to handle YouTube's changes.
- ✅ **Containerized**: Runs in a Docker container for easy deployment and portability.
- ✅ **MCP Compliant**: Implements the Multi-party Computation Protocol (MCP) for easy integration with other tools.
- ✅ **Secure**: Protects the server with API key authentication.

---

## 🐳 Docker Deployment

### Prerequisites

- [Docker](https://www.docker.com/) installed.
- [Docker Compose](https://docs.docker.com/compose/) installed.

### 1. Configure API Keys

Before building the container, you need to configure the API keys. Create a file named `api_keys.json` in the root of the project and add a list of valid API keys.

**Example `api_keys.json`:**
```json
{
  "keys": [
    "your-super-secret-api-key"
  ]
}
```

### 2. Build and Run the Container

From the project's root directory, run the following command to build and run the Docker container in detached mode:

```bash
docker-compose up -d --build
```

The server will be running on `http://localhost:5000`.

---

## 💡 Usage

The server exposes two endpoints:

*   `/test_transcript`: A simple endpoint for testing the transcript fetching functionality.
*   `/`: The main endpoint that implements the MCP protocol.

### Authentication

All endpoints are protected with API key authentication. You need to provide a valid API key in the `X-API-KEY` header of your request.

Authentication can be disabled by setting the `AUTH_ENABLED` environment variable to `false` in the `docker-compose.yml` file.

### /test_transcript Endpoint

Make a GET request to the `/test_transcript` endpoint, providing the ID of the YouTube video and your API key.

**Example using `curl`:**
```bash
curl -H "X-API-KEY: your-super-secret-api-key" "http://localhost:5000/test_transcript?videoId=aT04DvIiovI"
```

### / Endpoint (MCP)

Make a POST request to the `/` endpoint with a JSON-RPC 2.0 message and your API key.

**Example using `curl`:**
```bash
curl -X POST -H "Content-Type: application/json" -H "X-API-KEY: your-super-secret-api-key" -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"get_transcript","arguments":{"url":"https://www.youtube.com/watch?v=aT04DvIiovI"}}}' http://localhost:5000/
```

### Successful Response (`200 OK`)

If successful, the server returns a JSON object containing the transcript. The transcript is provided as a JSON object with `start`, `end`, and `text` fields for each caption.

### Error Response

If the API key is invalid, the server will return a `401 Unauthorized` error.

If the `videoId` parameter is missing or the transcript cannot be fetched, the server will return an error message.
