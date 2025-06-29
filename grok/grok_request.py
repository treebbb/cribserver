#! /usr/bin/env python3
'''
https://console.x.ai
'''

import curses
from curses import wrapper
import json
import os
import sys
import re
import time
from typing import List, Tuple
from openai import OpenAI

ASSISTANT = 'assistant'
SYSTEM_PROMPT = open('grok/instructions.txt', 'r').read()

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
        # Initialize conversation history with a system prompt
        self.conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]  # list of dicts {role: x, content: x}
        self.display_history = []  # For rendering in curses
        for dir_idx in range(100):
            self.output_dir = os.path.join(self.OUTPUT_DIR, str(dir_idx).zfill(4))
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                break

    def _process_file_content(self, input_str):
        """Process lines starting with 'file:' to include file contents."""
        result = ""
        for line in input_str.splitlines():
            if line.startswith('file:'):
                filepath = line[5:].strip()
                ext = os.path.splitext(filepath)[1]
                if ext == '.py':
                    comment_begin, comment_end = '#', '#'
                else:
                    comment_begin, comment_end = '/*', '*/'
                result += f"{comment_begin} BEGIN {filepath} {comment_end}\n"
                result += open(filepath, 'r').read()
                result += f"\n{comment_begin} END {filepath} {comment_end}\n"
            else:
                result += line + "\n"
        return result

    def _save_code_blocks_to_files(self, response: str, output_dir: str = "./") -> str:
        """Extract code blocks from response and save them to files."""
        code_block = []
        new_response = []

        for line in response.splitlines():
            if line.startswith('```'):
                if len(code_block) > 10:
                    filename = code_block[0].split()[-1]
                    filename = re.sub(r'[^a-z0-9._-]', '_', filename)
                    if not filename or filename.startswith('___'):
                        for code_idx in range(100):
                            filename = f'code_block_{code_idx}'
                            filepath = os.path.join(self.output_dir, filename)
                            if not os.path.exists(filepath):
                                break
                    else:
                        filepath = os.path.join(self.output_dir, filename)
                    with open(filepath, 'w') as f:
                        for line in code_block[1:]:
                            f.write(line)
                            f.write('\n')
                    new_response.append(f'<code block {filepath}>')
                    code_block.clear()
                elif code_block:
                    new_response.extend(code_block)
                    code_block.clear()
                else:
                    code_block.append(line)
            elif code_block:
                code_block.append(line)
            else:
                new_response.append(line)
        return '\n'.join(new_response)

    def query_grok(self):
        """Send the conversation history to the xAI Grok API and return the response."""
        history = []
        for request in self.conversation_history:
            if request['role'] == 'user':
                request = request.copy()
                request['content'] = self._process_file_content(request['content'])
            history.append(request)
        filename = str(time.time()) + '_request.json'
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(history, f, indent=2)
        try:
            completion = self.client.chat.completions.create(
                model=self.MODEL,
                messages=history,
                temperature=0.7,
                max_tokens=5000
            )
            filename = str(time.time()) + '_response.json'
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'w') as f:
                json.dump(completion.to_dict(), f, indent=2)
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"

class GrokCursesApp:
    def __init__(self, stdscr, chat):
        self.stdscr = stdscr
        self.chat = chat
        self.input_buffer = []
        self.scroll_offset = 0
        self.setup_windows()

    def setup_windows(self):
        """Set up the curses windows for input, output, and status with color support."""
        self.stdscr.clear()
        self.height, self.width = self.stdscr.getmaxyx()
    
        # Initialize color support
        if curses.has_colors():
            curses.start_color()
            curses.init_color(curses.COLOR_BLACK, 0, 0, 0)
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Status bar color
            self.color_pair = curses.color_pair(1)
            self.status_color_pair = curses.color_pair(3)
        else:
            self.color_pair = 0
            self.status_color_pair = 0
        # Status window (top 3 lines)
        self.status_win = curses.newwin(3, self.width, 0, 0)
        # Output window (below status window)
        self.output_win_height = self.height - 8  # Adjusted for status window
        self.output_win = curses.newwin(self.output_win_height, self.width, 3, 0)
        self.output_win.scrollok(True)
        # Input window (bottom part of screen)
        self.input_win = curses.newwin(5, self.width, self.height - 5, 0)
        self.input_win.scrollok(True)
        # init status display
        self.update_status()

    def update_status(self):
        """Update the status window with the number of requests made to Grok and the output directory."""
        self.status_win.clear()
        request_count = sum(1 for item in self.chat.conversation_history if item['role'] == 'user')
        status_text = f" Grok Requests: {request_count}    Output Dir: {self.chat.output_dir} "
        self.status_win.addstr(1, 0, status_text, self.status_color_pair)
        self.status_win.refresh()

    def resize_windows(self):
        """Handle window resizing."""
        self.height, self.width = self.stdscr.getmaxyx()
        self.status_win.resize(3, self.width)
        self.output_win_height = self.height - 8
        self.output_win.resize(self.output_win_height, self.width)
        self.output_win.mvwin(3, 0)
        self.input_win.resize(5, self.width)
        self.input_win.mvwin(self.height - 5, 0)
        self.update_status()
        self.redraw()

    def redraw(self):
        """Redraw the output window content with line wrapping and color."""
        self.output_win.clear()
        visible_lines = self.output_win_height - 1
        start_idx = max(0, len(self.chat.display_history) - visible_lines + self.scroll_offset)
        end_idx = min(len(self.chat.display_history), start_idx + visible_lines)

        max_width = self.width - 1  # Maximum width per line
        current_row = 0  # Track current row in window

        for history_item in self.chat.display_history[start_idx:end_idx]:
            if current_row >= visible_lines:
                break
            line = history_item['content']
            role = history_item['role']
            if role == ASSISTANT:
                color_pair = curses.color_pair(1)
            else:
                color_pair = curses.color_pair(2)                
            # Process the line with wrapping
            while line and current_row < visible_lines:
                if len(line) <= max_width:
                    # Line fits entirely, display it
                    try:
                        self.output_win.addstr(current_row, 0, line, color_pair)
                        current_row += 1
                    except curses.error:
                        pass
                    break
                else:
                    # Find split point
                    split_pos = max_width
                    # Look for a space within the last 20 characters
                    search_start = max(0, max_width - 20)
                    last_space = line[search_start:max_width].rfind(' ')

                    if last_space != -1:
                        # Found a space, adjust split position
                        split_pos = search_start + last_space

                    # Display the segment up to split_pos
                    try:
                        self.output_win.addstr(current_row, 0, line[:split_pos], color_pair)
                        current_row += 1
                        # Move to next segment, skip the space if we split on one
                        line = line[split_pos + 1 if last_space != -1 else split_pos:].lstrip()
                    except curses.error:
                        break

        self.output_win.refresh()

    def run(self):
        """Run the main conversation loop with curses UI."""
        curses.curs_set(1)  # Show cursor
        self.input_win.move(1, 0)
        current_input = ""

        while True:
            try:
                key = self.input_win.getch()

                if key == curses.KEY_RESIZE:
                    self.resize_windows()

                elif key == 4:  # Ctrl+D
                    if current_input:
                        d = {"role": "user", "content": current_input}
                        self.chat.conversation_history.append(d)
                        self.chat.display_history.append(d)
                        self.redraw()
                        self.update_status()  # Update status after new request

                        self.input_win.clear()
                        self.input_win.addstr(0, 0, "Input (Ctrl+D to send, Ctrl+C to exit):", self.color_pair)
                        self.input_win.refresh()
                        current_input = ""

                        response = self.chat.query_grok()
                        processed_response = self.chat._save_code_blocks_to_files(response)
                        d = {"role": ASSISTANT, "content": processed_response}
                        self.chat.conversation_history.append(d)
                        self.chat.display_history.append(d)
                        self.redraw()

                elif key == curses.KEY_UP:
                    self.scroll_offset += 1
                    self.redraw()

                elif key == curses.KEY_DOWN:
                    self.scroll_offset -= 1
                    if self.scroll_offset < 0:
                        self.scroll_offset = 0
                    self.redraw()

                elif key == 10:  # Enter
                    self.input_win.addstr("\n")
                    current_input += "\n"
                    self.input_win.refresh()

                elif key == curses.KEY_BACKSPACE or key == 127:
                    if current_input:
                        current_input = current_input[:-1]
                        y, x = self.input_win.getyx()
                        if x == 0:
                            y -= 1
                            x = self.width - 1
                        else:
                            x -= 1
                        self.input_win.move(y, x)
                        self.input_win.delch()
                        self.input_win.refresh()

                elif 32 <= key <= 126:  # Printable characters
                    current_input += chr(key)
                    self.input_win.addch(key, self.color_pair)
                    self.input_win.refresh()

            except KeyboardInterrupt:
                break

def main(stdscr):
    """Entry point for the curses application."""
    if not os.getenv("XAI_API_KEY"):
        print("Error: XAI_API_KEY environment variable not set.")
        sys.exit(1)

    chat = GrokChat()
    app = GrokCursesApp(stdscr, chat)
    app.run()

if __name__ == "__main__":
    wrapper(main)
