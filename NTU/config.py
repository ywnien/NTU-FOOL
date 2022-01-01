import json
from getpass import getpass
from pathlib import Path

json_dump = lambda dictionary, file: json.dump(
    dictionary, file, indent=4, ensure_ascii=False
)
JSON = Path(__file__).parents[1]/'json'


def initialize():
    student_id = input('Student ID: ')
    password = getpass('Password: ', None)
    file_directory = Path(input('File directory: ') or 'fool')
    file_directory.mkdir(parents=True, exist_ok=True)

    d = {
        'student_id': student_id,
        'password': password,
        'file_directory': str(file_directory),
    }

    JSON.mkdir(parents=True, exist_ok=True)
    with open(JSON/'config.json', 'w', encoding='utf8') as f:
        json_dump(d, f)