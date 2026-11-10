# AI Code Assistant

A small Python command-line tool that generates code snippets from natural-language prompts using the OpenAI API.

## How it works

- Prompts you for a coding request in the terminal
- Sends the prompt to the OpenAI Completions API (`text-davinci-002`)
- Prints the generated code

## Run it

```bash
pip install openai
# add your API key in AIChat.py
python AIChat.py
```

## Status

An early learning project from my first experiments with the OpenAI API. It uses the legacy Completions endpoint; my current AI work uses modern chat models and agent tooling — see AI_Agents_Chat and GeoGPT on my profile.
