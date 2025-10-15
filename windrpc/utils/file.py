import os
import shutil


def read_lines(path):
    with open(path, 'r', encoding='utf-8') as file:
        return file.readlines()


def copy(source_path, dest_path):
    try:
        shutil.copy2(source_path, dest_path)
        print(f"'{source_path}' is copied to '{dest_path}'")
    except FileNotFoundError:
        print(f"error: '{source_path}' is not found")
    except Exception as e:
        print(f"error: {e}")


def write(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
