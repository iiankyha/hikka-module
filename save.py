import os
import sys
import time
import random
import webbrowser
from pathlib import Path


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def typewriter(text, delay=0.05):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def random_quote():
    quotes = [
        "Код — это поэзия, написанная логикой.",
        "Одиночество — это возможность сосредоточиться на своем коде.",
        "Лучший способ разобраться — это написать код.",
        "Компьютер не будет критиковать твой код, если ты не попросишь.",
        "В тишине своего кода я нахожу свободу.",
        "Каждая строчка кода — это шаг к совершенству.",
        "Мир слишком громкий, зато мой код всегда говорит в нужной тональности.",
    ]
    return random.choice(quotes)


def create_project_structure(base_path="."):
    dirs = [
        "src",
        "tests",
        "docs",
        "data/input",
        "data/output",
        "utils",
        "logs"
    ]
    
    for dir_path in dirs:
        full_path = os.path.join(base_path, dir_path)
        os.makedirs(full_path, exist_ok=True)
        print(f"Создана папка: {full_path}")
    
    files = {
        "README.md": "# Мой проект\n\nОписание проекта...",
        "src/main.py": 'print("Hello, World!")',
        ".gitignore": "*.pyc\n__pycache__/\n*.log\n",
    }
    
    for file_path, content in files.items():
        full_path = os.path.join(base_path, file_path)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Создан файл: {full_path}")


def open_docs(query):
    docs_sites = {
        'python': 'https://docs.python.org/3/',
        'mdn': 'https://developer.mozilla.org/',
        'so': 'https://stackoverflow.com/',
        'github': 'https://github.com/',
        'pypi': 'https://pypi.org/'
    }
    
    site = docs_sites.get(query.lower(), docs_sites['python'])
    webbrowser.open(site)


def count_loc(file_path):
    loc = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                loc += 1
    return loc


def simple_timer(minutes):
    seconds = minutes * 60
    print(f"Таймер запущен на {minutes} минут. Работайте сосредоточенно.")
    
    for remaining in range(seconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        timer = f"{mins:02d}:{secs:02d}"
        print(timer, end="\r")
        time.sleep(1)
    
    print("\nВремя вышло! Сделайте перерыв.")
    try:
        import winsound
        winsound.Beep(1000, 1000)
    except:
        print("\a")


def get_file_tree(start_path=".", max_depth=3):
    start_path = Path(start_path)
    file_tree = {
        "name": start_path.name,
        "type": "directory",
        "path": str(start_path),
        "children": []
    }
    
    if max_depth <= 0:
        return file_tree
    
    try:
        for item in start_path.iterdir():
            if item.is_dir():
                file_tree["children"].append(
                    get_file_tree(item, max_depth - 1))
            else:
                file_tree["children"].append({
                    "name": item.name,
                    "type": "file",
                    "path": str(item),
                    "size": item.stat().st_size
                })
    except PermissionError:
        pass
    
    return file_tree


def print_file_tree(tree, indent=""):
    if tree["type"] == "directory":
        print(f"{indent}📁 {tree['name']}/")
        new_indent = indent + "    "
        for child in tree["children"]:
            print_file_tree(child, new_indent)
    else:
        size_kb = tree["size"] / 1024
        print(f"{indent}📄 {tree['name']} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    clear_screen()
    typewriter("Добро пожаловать в Hikke Utils!")
    print(random_quote())
    
    print("\nПримеры использования:")
    print("1. Создание структуры проекта:")
    create_project_structure("./demo_project")
    
    print("\n2. Дерево файлов (макс. глубина 2):")
    tree = get_file_tree(".", 2)
    print_file_tree(tree)
    
    print("\n3. Таймер Pomodoro (1 минута для демо):")
    simple_timer(1)
