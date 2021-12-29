import json
from getpass import getpass
from pathlib import Path

json_dump = lambda dictionary, file: json.dump(
    dictionary, file, indent=4, ensure_ascii=False
)
JSON = Path(__file__).parent.parent/'json'

try:
    with open(JSON/'config.json', 'r') as f:
        d = json.load(f)
        student_id = d['student_id']
        password = d['password']
        FOOL = Path(d['file_directory'])
except:
    pass


def initialize():
    student_id = input('Student ID: ')
    password = getpass('Password: ', None)
    file_directory = input('File directory: ')
    d = {
        'student_id': student_id,
        'password': password,
        'file_directory': file_directory,
    }
    
    JSON.mkdir(parents=True, exist_ok=True)
    with open(JSON/'config.json', 'w') as f:
        json_dump(d, f)