#! /usr/bin/env python3

from openai import OpenAI
import os
import sys
import re
from typing import List, Tuple

class GrokChat:
    MODEL = "grok-3"
    ENDPOINT = "https://api.x.ai/v1"
    OUTPUT_DIR = "grok_output"

    def __init__(self):
        """Initialize the GrokChat client with API key and conversation history."""
        self.client = OpenAI(
            api_key=os.getenv("XAI_API_KEY"),
            base_url=self.ENDPOINT,
        )
        self.conversation_history = []
        # Create output directory if it doesn't exist
        if not os.path.exists(self.OUTPUT_DIR):
            os.makedirs(self.OUTPUT_DIR)

    def _process_file_content(self, line):
        """Process lines starting with 'file:' to include file contents."""
        if line.startswith('file:'):
            filepath = line[5:].strip()
            content = f"/* BEGIN {filepath} */\n"
            content += open(filepath, 'r').read()
            content += f"\n/* END {filepath} */"
            return content
        return line

    def _save_code_blocks_to_files(self, response: str, output_dir: str = "./") -> str:
        """
        Extract code blocks from the response, save them to files, and replace the code blocks
        with the filenames in the response text.

        ```python test.py
        def hello():
        print("Hello, World!")
        ```
        
        Args:
            response (str): The response text containing code blocks.
            output_dir (str): Directory where the files will be saved. Defaults to current directory.
        
        Returns:
            Tuple[str, List[str]]: A tuple containing the modified response text (with code blocks replaced by filenames)
                                   and a list of saved file paths.
        """
        code_block = []
        new_response = []
        
        for line in response.splitlines():
            if line.startswith('```'):
                if len(code_block) > 10:
                    # write contents
                    filename = code_block[0].split()[-1]
                    filename = re.sub(r'[^a-z0-9._-]', '_', filename)
                    if not filename or filename.startswith('___'):
                        for code_idx in range(100):
                            filename = f'code_block_{code_idx}'
                            filepath = os.path.join(self.OUTPUT_DIR, filename)
                            if not os.path.exists(filepath):
                                break
                    else:
                        filepath = os.path.join(self.OUTPUT_DIR, filename)
                    with open(filepath, 'w') as f:
                        for line in code_block[1:]:
                            f.write(line)
                            f.write('\n')
                    new_response.append(f'<code block {filepath}>')
                    code_block.clear()
                elif code_block:
                    # inline short blocks
                    new_response.extend(code_block)
                    code_block.clear()
                else:
                    # start code block
                    code_block.append(line)
            elif code_block:
                code_block.append(line)
            else:
                new_response.append(line)
        return '\n'.join(new_response)

    def get_user_input(self):
        """Prompt user for input until Ctrl-D is pressed."""
        print("\nEnter your message (press Ctrl-D to finish, type 'exit' to quit):")
        lines = []
        try:
            while True:
                line = input()
                processed_line = self._process_file_content(line)
                lines.append(processed_line)
        except EOFError:
            return "\n".join(lines).strip()

    def query_grok(self):
        """Send the conversation history to the xAI Grok API and return the response."""
        try:
            completion = self.client.chat.completions.create(
                model=self.MODEL,
                messages=self.conversation_history,
                temperature=0.7,
                max_tokens=5000
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

    def run(self):
        """Run the main conversation loop."""
        # Check if API key is set
        if not os.getenv("XAI_API_KEY"):
            print("Error: XAI_API_KEY environment variable not set.")
            sys.exit(1)

        print("Starting Grok conversation. Type 'exit' or press Ctrl-C to quit.")

        while True:
            # Get user input
            prompt = self.get_user_input()

            # Check for exit condition
            if prompt.lower() == "exit" or not prompt:
                print("Exiting conversation.")
                break

            # Add user message to conversation history
            self.conversation_history.append({"role": "user", "content": prompt})

            # Query the API with the full conversation history
            response = self.query_grok()

            # Add assistant response to conversation history (before saving files)
            self.conversation_history.append({"role": "assistant", "content": response})

            # Process response to save code blocks to files
            response = self._save_code_blocks_to_files(response)

            # Print the response
            print("\nGrok response:")
            print(response)

def main():
    """Entry point for the application."""
    try:
        chat = GrokChat()
        chat.run()
    except KeyboardInterrupt:
        print("\nExiting conversation (Ctrl-C).")
        sys.exit(0)

if __name__ == "__main__":
    main()
