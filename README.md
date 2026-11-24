# AI Code Assistant

A small Python web app that generates code snippets from natural-language prompts using the OpenAI API.

## How it works

- Provides a responsive GitHub-style chat interface
- Sends prompts to a modern OpenAI chat model
- Shows generated code in copy-ready blocks
- Keeps the original terminal interface available

## Run it

```bash
pip install -r requirements.txt
set OPENAI_API_KEY=your_api_key
python app.py
```

Open `http://127.0.0.1:5000`.
Create an account on the sign-up screen, or sign in after registering.
Set `FLASK_SECRET_KEY` to a strong private value before exposing the app beyond your local machine.

## Social sign-in

Google, Apple, and GitHub buttons are enabled by registering OAuth applications and setting these environment variables:

```bash
set GOOGLE_CLIENT_ID=...
set GOOGLE_CLIENT_SECRET=...
set GITHUB_CLIENT_ID=...
set GITHUB_CLIENT_SECRET=...
set APPLE_CLIENT_ID=...
set APPLE_CLIENT_SECRET=...
set FLASK_SECRET_KEY=...
```

Callback URLs:

- Google: `http://127.0.0.1:5000/auth/google/callback`
- GitHub: `http://127.0.0.1:5000/auth/github/callback`
- Apple: `http://127.0.0.1:5000/auth/apple/callback`

To use the original terminal interface:

```bash
python AIChat.py
```

## Status

An early learning project from my first experiments with the OpenAI API. It uses the legacy Completions endpoint; my current AI work uses modern chat models and agent tooling — see AI_Agents_Chat and GeoGPT on my profile.
