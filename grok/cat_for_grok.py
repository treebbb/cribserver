#! /usr/bin/env python3

import os

def print_file(file_path):
    ext = os.path.splitext(file_path)[1]
    # Print filename as C++ comment
    print(f"/* BEGIN {file_path} */")
    try:
        # Read and print file contents
        with open(file_path, 'r', encoding='utf-8') as file:
            print(file.read())
            # Add a newline between files
            print(f"/* END {file_path} */")
            print()
    except Exception as e:
        print(f"Error reading {filename}: {str(e)}")


def add_files(dirname, file_list):
    # Process each file
    for filename in file_list:
        file_path = os.path.join(dirname, filename)
        print_file(file_path)


def process_dir(dirname, ext):
    if not os.path.exists(dirname):
        print(f"Error: {dirname!r} directory not found")
        exit(1)
    files = os.listdir(dirname)
    file_list = sorted([f for f in files if f.endswith(ext)])
    add_files(dirname, file_list)


def main():
    '''
    git ls-tree -r main --name-only
    '''
    import sys
    args = sys.argv[1:]
    if args:
        for filename in args:
            print_file(filename)
    else:
        process_dir('grok', '.txt')
        process_dir('src/python/cribserver', '.py')
        process_dir('./', '.py')


main()
