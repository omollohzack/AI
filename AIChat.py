import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


def generate_code(prompt, api_key=None, base_url=None, model=None):
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    base_url = base_url or os.getenv("OPENAI_BASE_URL")
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not api_key:
        raise RuntimeError("Add an API key in Model Settings before generating code.")
    if OpenAI is None:
        raise RuntimeError("Install the project dependencies with: pip install -r requirements.txt")

    client_options = {"api_key": api_key}
    if base_url:
        client_options["base_url"] = base_url
    client = OpenAI(**client_options)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert programming assistant. Return useful, concise code "
                    "with a short explanation. Prefer complete answers over snippets."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=1024,
        temperature=0.5,
    )
    return response.choices[0].message.content.strip()


def main():
    print("Welcome to the AI Code Assistant!")
    while True:
        prompt = input("Enter your prompt or 'q' to quit: ").strip()
        if prompt.lower() == "q":
            break
        if not prompt:
            continue
        try:
            code = generate_code(prompt)
        except RuntimeError as error:
            print(error)
            continue
        print("\nGenerated code:\n")
        print(code)
        print()


if __name__ == "__main__":
    main()
