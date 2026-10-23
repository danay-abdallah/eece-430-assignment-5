# EECE430 Assignment 5 - AI Agent with Docker
Danay Abdallah

This is the AI Inventory Agent from Assignment 3, packaged for Docker.
It uses Django, SQLite, and Gemini and includes the item price and VAT tools.

## Build and run
Install and start Docker Desktop. In this repository's root:

```sh
docker build -t ai-agent-app .
cp .env.example .env
```
Enter your own Gemini API key in `.env`. Do not commit this file.
Then run:

```sh
docker run -d --name ai-agent -p 127.0.0.1:8000:8000 --env-file .env ai-agent-app
docker exec ai-agent python manage.py loaddata demo_inventory
```
Open http://localhost:8000/. The server applies migrations automatically.
The fixture supplies a sample chocolate bar price of 2.50. Three bars with
10% VAT cost 8.25. Live chat requires a valid API key and an available Gemini model.
The original project's model can be overridden using GEMINI_MODEL in `.env`.

Optional admin account:
```sh
docker exec -it ai-agent python manage.py createsuperuser
```
SQLite data is stored inside the container and is lost if the container is removed.
This uses Django's development server for the local lab demonstration.

## Run the published image from GitHub

The GitHub Actions workflow builds and tests the image, publishes it to GHCR,
then pulls it back and starts the container. Its logs provide execution evidence.
A live Gemini response requires your own API key; the automated checks do not
call Gemini.

```sh
docker pull ghcr.io/danay-abdallah/eece430-assignment5-ai-agent:latest
docker run -d --name ai-agent -p 127.0.0.1:8000:8000 --env-file .env ghcr.io/danay-abdallah/eece430-assignment5-ai-agent:latest
docker exec ai-agent python manage.py loaddata demo_inventory
```

The published image targets Linux amd64 (GitHub's runner). On an Apple Silicon
Mac, add `--platform linux/amd64` to pull/run, or build locally for native ARM.
If the package is private, sign in to GHCR with a token with read:packages
permission before pulling, or use the source build instructions above.

## Verification

Six application tests passed locally. Check the latest green Actions run for
Docker build, container tests, registry publication, and HTTP smoke test results.
The smoke test checks application startup; chat tests mock Gemini responses.
