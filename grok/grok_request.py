#! /usr/bin/env python3

from openai import OpenAI
import os
import sys

#MODEL = "grok-3-latest"  # works but gives grok2
MODEL = "grok-3"
#MODEL = "grok-beta"  # doesn't work
ENDPOINT = "https://api.x.ai/v1"
#ENDPOINT = "https://api.x.ai/v1/chat/completions"  # doesn't work

# Initialize the OpenAI client for xAI's API
client = OpenAI(
    api_key=os.getenv("XAI_API_KEY"),  # Your xAI API token
    base_url=ENDPOINT,
)

# Store conversation history
conversation_history = []


def get_user_input():
    """Prompt user for input until Ctrl-D is pressed."""
    print("\nEnter your message (press Ctrl-D to finish, type 'exit' to quit):")
    lines = []
    try:
        while True:
            line = input()
            if line.startswith('file:'):
                filepath = line[5:].strip()
                line = f"/* BEGIN {filepath} */"
                line += "\n"
                line += open(filepath, 'r').read()
                line += "\n"
                line += f"/* END {filepath} */"
            lines.append(line)
    except EOFError:
        return "\n".join(lines).strip()

def query_grok(messages):
    """Send the conversation history to the xAI Grok API and return the response."""
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,  # Controls randomness (0 to 2)
            max_tokens=5000  # Adjust as needed
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def main():
    # Check if API key is set
    if not os.getenv("XAI_API_KEY"):
        print("Error: XAI_API_KEY environment variable not set.")
        sys.exit(1)

    print("Starting Grok conversation. Type 'exit' or press Ctrl-C to quit.")

    while True:
        # Get user input
        prompt = get_user_input()

        # Check for exit condition
        if prompt.lower() == "exit" or not prompt:
            print("Exiting conversation.")
            break

        # Add user message to conversation history
        conversation_history.append({"role": "user", "content": prompt})

        # Query the API with the full conversation history
        response = query_grok(conversation_history)

        # Add assistant response to conversation history
        conversation_history.append({"role": "assistant", "content": response})

        # Print the response
        print("\nGrok response:")
        print(response)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting conversation (Ctrl-C).")
        sys.exit(0)
