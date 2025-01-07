import openai
import os

# Set up OpenAI API key
openai.api_key = "your_api_key"

def generate_code(prompt):
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        max_tokens=1024,
        n=1,
        stop=None,
        temperature=0.5,
    )
    return response.choices[0].text.strip()

def main():
    print("Welcome to the AI Code Assistant!")
    while True:
        prompt = input("Enter your prompt or 'q' to quit: ")
        if prompt.lower() == 'q':
            break
        code = generate_code(prompt)
        print("Generated code:")
        print(code)
        print("")

if __name__ == "__main__":
    main()
