# Project Overview

This project is a server that provides a service to fetch transcripts from YouTube videos. It is designed to be deployed as a Docker container, making it easy to run on any platform that supports Docker.

The core functionality is exposed through a JSON-RPC 2.0 endpoint that conforms to the MCP protocol, allowing it to be integrated with other tools and services. It also provides a simple RESTful endpoint for direct testing.

## Key Technologies

*   **Docker:** The project is designed to be run as a Docker container.
*   **Python:** The server is written in Python, using the Flask framework.
*   **yt-dlp:** The server uses the `yt-dlp` command-line tool to fetch transcripts from YouTube.
*   **MCP (Multi-party Computation Protocol):** The primary endpoint uses plain JSON-RPC 2.0 to communicate following the MCP protocol.
*   **Flask-Cors:** Handles Cross-Origin Resource Sharing (CORS) for web-based clients.
*   **webvtt-py:** Used to parse VTT transcript files into a JSON structure.
*   **Node.js & ffmpeg:** Included in the Docker image to provide a JS runtime and processing tools for `yt-dlp`.

# Building and Running

## Prerequisites

*   [Docker](https://www.docker.com/) installed.
*   [Docker Compose](https://docs.docker.com/compose/) installed.

## Build and Run the Container

From the project's root directory, run the following command to build and run the Docker container in detached mode:

```bash
docker-compose up -d --build
```

The server will be running on `http://localhost:5000`.

# Development Conventions

*   **Configuration:** The project is configured using the `Dockerfile` and `docker-compose.yml` files. The `docker-compose.yml` file includes the `AUTH_ENABLED` environment variable to enable or disable API key authentication.
*   **Entry Point:** The main logic of the server is in `server.py`.
*   **MCP Protocol:** The server implements the MCP protocol over plain JSON-RPC on the `/` endpoint. This includes methods like `initialize`, `tools/list`, and `tools/call`.
*   **Testing:** A simple test endpoint is available at `/test_transcript` to fetch a transcript for a given video ID.
    Example: `http://localhost:5000/test_transcript?videoId=<VIDEO_ID>`