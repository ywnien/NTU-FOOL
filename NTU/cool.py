import json
import re
from asyncio import create_task, get_running_loop, run
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from bs4 import BeautifulSoup, Doctype
from requests import Session

from NTU.config import initialize

json_dump = lambda dictionary, file: json.dump(
    dictionary, file, indent=4, ensure_ascii=False
)
Item = namedtuple('Item', 'category, title, url')

JSON = Path(__file__).parents[1]/'json'
SRC = Path(__file__).parents[1]/'src'
HEAD = SRC/'head.html'

try:
    with open(JSON/'config.json', 'r', encoding='utf8') as f:
        d = json.load(f)
        student_id = d['student_id']
        password = d['password']
        FOOL = Path(d['file_directory'])
except FileNotFoundError:
    initialize()
    with open(JSON/'config.json', 'r', encoding='utf8') as f:
        d = json.load(f)
        student_id = d['student_id']
        password = d['password']
        FOOL = Path(d['file_directory'])

class Cool(Session):
    DOMAIN = 'https://cool.ntu.edu.tw'
    MODULE_ITEM = {'class': ['ig-title', 'title', 'item_link']}

    def __init__(
            self, semester=None, student_id=student_id, password=password
        ):
        super().__init__()
        self.login(student_id, password)
        self.courses = self.read_courses()
        self.semester = self.check_semester(semester)
        self.checkpoints = self.read_checkpoints()

    def login(self, student_id, password):
        headers = {
            'user-agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
                ' AppleWebKit/537.36 (KHTML, like Gecko)'
                ' Chrome/95.0.4638.69 Safari/537.36'
            )
        }
        self.headers.update(headers)
        r1 = self.get(f'{self.DOMAIN}/login/saml')

        responsed_url = (
            'https://adfs.ntu.edu.tw' +
            re.search(r'action="(.*?)" id="MainForm"', r1.text).group(1)
        )
        payload = {
            '__EVENTVALIDATION': re.search(
                r'__EVENTVALIDATION" value="(.*?)" />', r1.text
            ).group(1),
            '__VIEWSTATE': re.search(
                r'__VIEWSTATE" value="(.*?)" />', r1.text
            ).group(1),
            '__VIEWSTATEGENERATOR': re.search(
                r'__VIEWSTATEGENERATOR" value="(.*?)" />', r1.text
            ).group(1),
            '__db': re.search(r'__db" value="(.*?)" />', r1.text).group(1),
            'ctl00$ContentPlaceHolder1$PasswordTextBox': f'{password}',
            'ctl00$ContentPlaceHolder1$SubmitButton': '登入',
            'ctl00$ContentPlaceHolder1$UsernameTextBox': f'{student_id}',
        }
        r2 = self.post(responsed_url, data=payload)

        payload = {
            'SAMLResponse': re.search(
                r'name="SAMLResponse" value="(.*?)" />', r2.text
            ).group(1),
        }
        self.post(f'{self.DOMAIN}/login/saml', data=payload)

    @property
    def semesters(self) -> list:
        """
        Returning a list containing keys of `Cool.courses`.
        Semesters are sorted from low to high.

        return: `list[str]`
        """
        keys = sorted(list(self.courses.keys())) # order: small -> large
        return keys

    def set_semester(self, semester=None):
        """
        Setting `self.semester` with checking.

        If the argument `semester` is wrong, setting this semester by default.

        argument:
        - semester: `str`
        """
        self.semester = self.check_semester(semester)

    def check_semester(self, semester):
        if semester:
            return self.search(self.semesters, semester)
        else:
            return self.semesters[-1] # this semester

    def search(self, target: list, search: str, _match=None) -> str:
        if _match:
            _match = [name for name in _match if search in name]
        else:
            _match = [name for name in target if search in name]

        if len(_match) == 1:
            return _match[0]
        elif len(_match) == 0:
            print('No result. Please search again!\n')
            search = input('Search: ')
            return self.search(target, search)
        else:
            print(*_match, sep='  ')
            search = input('\nSearch: ')
            return self.search(target, search, _match)

    def search_course(self, search: str) -> str:
        return self.search(self.courses[self.semester].keys(), search)

    def read_courses(self) -> dict:
        """
        Reading `/json/courses.json` and return it as a dictonary.

        If raising `FileNotFoundError`, write `/json/courses.json`.

        return: `dict`
        """
        try:
            with open(JSON/'courses.json', 'r', encoding='utf8') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_courses()

    def get_courses(self):
        """
        Getting semesters and courses from https://cool.ntu.edu.tw/courses.

        And writting to `json/courses.json`.

        return: `dict`
        """
        r = self.get(f'{self.DOMAIN}/courses')
        soup = BeautifulSoup(r.text, 'lxml')
        course_rows = soup('tr', class_='course-list-table-row')

        _courses = {} # naming _courses to distinguish from self.courses
        for course_row in course_rows:
            try:
                semester = course_row.find(
                    'td', class_="course-list-term-column"
                ).string.strip()
                info = course_row.find('a', href=True)
            except Exception as e:
                print(f'{str(e)}: self.courses ignored a course.')

            _courses.setdefault(semester, {})[info['title']] = info['href']

        ordered_keys = sorted(list(_courses.keys()))
        _courses = {key: _courses[key] for key in ordered_keys}

        with open(JSON/'courses.json', 'w', encoding='utf8') as f:
            json_dump(_courses, f)

        return _courses

    def save_modules(self, modules: dict, course_name: str, skip_check=False):
        if skip_check:
            pass
        else:
            course_name = self.search_course(course_name)

        try:
            with open(JSON/f'{self.semester}.json', 'r', encoding='utf8') as f:
                saved = json.load(f)
        except FileNotFoundError:
            with open(JSON/f'{self.semester}.json', 'w', encoding='utf8') as f:
                saved = {}
                json_dump(saved, f)

        saved.setdefault(course_name, {}).update(modules)

        with open(JSON/f'{self.semester}.json', 'w', encoding='utf8') as f:
            json_dump(saved, f)

    def read_modules(self, course_name: str) -> dict:
        """
        Reading `json/{self.semester}.json`
        and returning modules of `course_name`.
        """
        course_name = self.search_course(course_name)

        try:
            with open(JSON/f'{self.semester}.json', 'r', encoding='utf8') as f:
                return json.load(f)[course_name]
        except FileNotFoundError:
            with open(JSON/f'{self.semester}.json', 'w', encoding='utf8') as f:
                return self.get_modules(course_name)

    def get_modules(self, course_name: str):
        course_name = self.search_course(course_name)
        href = self.courses[self.semester][course_name]
        checkpoint = self.checkpoints[self.semester][course_name]

        print(f'Scraping: {course_name}...', end=' ', flush=True)
        soup = BeautifulSoup(
            self.get(f'{self.DOMAIN}{href}/modules').text,
            'lxml'
        )
        context_module = soup('div', id=re.compile(r'context_module_\d+'))

        switch = {
            'External Url': self._external_url,
            'Attachment': self._attachment,
            'Context Module Sub Header': self._sub_header,
        }
        modules = {}
        for i, block in enumerate(context_module[checkpoint:]):
            name = block.find('h2').text # context_module title
            for tag in block(
                'div', {'class': ['ig-row', 'ig-published', 'student-view']}
            ):
                category = tag.find('span', class_='type_icon')['title']

                item = switch.get(
                    category, self._others
                )(category, tag)._asdict()

                modules.setdefault(name, []).append(item)
                self.checkpoints[self.semester][course_name] = i + checkpoint

        self.save_modules(modules, course_name, skip_check=True)
        self.save_checkpoints()
        print('Done')

        return modules

    def read_checkpoints(self):
        try:
            with open(JSON/'checkpoints.json', 'r', encoding='utf8') as f:
                return json.load(f)
        except FileNotFoundError:
            checkpoints = {}
            for semester, courses in self.courses.items():
                checkpoints[semester] = {}
                for course in courses.keys():
                    checkpoints[semester][course] = 0
            self.checkpoints = checkpoints
            self.save_checkpoints()
            return checkpoints

    def save_checkpoints(self):
        with open(JSON/'checkpoints.json', 'w', encoding='utf8') as f:
            json_dump(self.checkpoints, f)

    def _external_url(self, category, tag: BeautifulSoup):
        try:
            info = tag.find('a', self.MODULE_ITEM)
            title = info['title'].strip()
            url = info['href']

            if 'http' in url:
                pass
            else:
                r = self.get(f'{self.DOMAIN}{url}')
                url = BeautifulSoup(r.text, 'lxml').select_one(
                    '#content > ul > li.active > span > a'
                )['href']

            return Item(category, title, url)

        except TypeError as e:
            print(f'{str(e)}')
            info = tag.find('a', class_='external')
            title = info['title'].strip()
            url = info['href']

            return Item(category, title, url)

    def _attachment(self, category, tag: BeautifulSoup):
        info = tag.find('a', self.MODULE_ITEM)
        title = info['title'].strip()
        url = info['href']

        download_link = BeautifulSoup(
            self.get(f'{self.DOMAIN}{url}').text, 'lxml'
        ).find('a', download='true')['href']

        return Item(category, title, download_link)

    def _sub_header(self, category, tag: BeautifulSoup):
        title = tag.find(
            'span', class_=['title', 'locked_title']
        )['title'].strip()
        return Item(category, title, None)

    def _others(self, category, tag: BeautifulSoup):
        info = tag.find('a', self.MODULE_ITEM)
        title = info['title'].strip()
        url = info['href']
        return Item(category, title, url)
    
    def _prompt(self) -> tuple:
        course_name = input('Course name: ')
        if course_name == '':
            return None, []
        else:
            course_name = self.search_course(course_name)

        modules = self.read_modules(course_name)
        module_titles = list(modules.keys()) # [module_title1, ...]
        module_titles.reverse()

        selected_items = []
        for module_title in module_titles:
            attachements = [
                item for item in modules[module_title]
                if item['category'] == 'Attachment'
            ]
            stop = False
            download_all = False
            for item in attachements:
                if download_all:
                    answer = 'y'
                else:
                    print(f'Download {module_title}: {item["title"]}?')
                    print('[Y] Yes\t[A] Yes to all\t[N] No\t[C] Cancel')
                    answer = input().lower()

                if answer == 'y':
                    selected_items.append(item)
                elif answer == 'a':
                    selected_items.append(item)
                    download_all = True
                elif answer == 'n':
                    pass
                else:
                    stop = True
                    break
            if stop:
                break

        return course_name, selected_items

    def download(self):
        async def coroutine():
            async def async_download():
                await loop.run_in_executor(
                    pool, lambda: self._download(course_name, item)
                )
        
            async def async_prompt():
                return await loop.run_in_executor(pool, self._prompt)

            loop = get_running_loop()
            with ThreadPoolExecutor() as pool:
                course_name = 'init'
                while course_name:
                    course_name, selected_items = (
                        await create_task(async_prompt())
                    )
                    for item in selected_items:
                        create_task(async_download())
                    

        run(coroutine())

    def _download(self, course_name, item: Item):
        path = FOOL/self.semester/course_name
        if path.exists():
            pass
        else:
            path.mkdir(parents=True, exist_ok=True)

        data = self.get(f'{self.DOMAIN}/{item["url"]}').content
        (path/item['title']).write_bytes(data)

    def update(self):
        for course_name in self.courses[self.semester].keys():
            self.get_modules(course_name)

    def new_semester(self):
        self.courses = self.get_courses()


class Fool:
    emoji = {
        'External Tool': '💻',
        'Discussion Topic': '💬',
        'Attachment': '📜',
        'External Url': '🔗',
        'Quiz': '📊',
        'Assignment': '📝',
        'Page': '📰',
    }

    def __init__(self, cool: Cool):
        self.c = cool
        self.nav_lang = 1 # 1 for Chinese, 2 for English

    @property
    def semester(self):
        return self.c.semester

    def set_nav_lang(self, lang):
        alias = {
            '中文': 'ch',
            'zh': 'ch',
            'ch': 'ch',
            'chinese': 'ch',
            'mandarin': 'ch',
            '英文': 'en',
            'english': 'en',
            'en': 'en'
        }
        d = {'ch': 1, 'en': 2}
        self.nav_lang = d[alias[lang]]
        self.nav_update()

    def set_semester(self, semester=None):
        """
        Setting `self.semester` with checking.

        If the argument `semester` is wrong, setting this semester by default.

        argument:
        - semester: `str`
        """
        self.c.semester = self.c.check_semester(semester)

    def nav_update(self):
        c = self.c
        soup = BeautifulSoup('<ul class="h_navbar"></ul>', 'html.parser')

        # TODO: add index.html
        #li_tags = [f'<li><a href="index.html">Home</a></li>']
        li_tags = [f'<li><a href={c.DOMAIN}/courses>NTU COOL</a></li>']
        for course_name in c.courses[self.semester].keys():
            try:
                string = re.search(
                    (
                        r'([A-z\u4e00-\u9fff\uff1a\uff08\uff09]+) '
                        r'([A-z1-9 \-\(\)\u2160-\u217f]+)'
                    ),
                    course_name
                ).group(self.nav_lang)
            except AttributeError:
                try:
                    string = re.search(
                        r'(.*?) ([A-z\u4e00-\u9fff]+)', course_name
                    ).group(2)
                except AttributeError:
                    pass

            href = f'{course_name}.html'
            li_tags.append(f'<li><a href="{href}">{string}</a></li>')

        li_str = '\n'.join(li_tags)
        soup.ul.append(BeautifulSoup(li_str, 'html.parser'))

        (SRC/f'{self.semester}_navbar.html').write_text(
            soup.prettify(), encoding='utf8'
        )

    def build(self):
        c = self.c
        with open(JSON/f'{self.semester}.json', 'r', encoding='utf8') as f:
            courses = json.load(f)

        for course_name, modules in courses.items():
            tags = [f'<h1>{course_name}</h1>']

            for module_title, items in modules.items():
                tags.append(f'<h2>{module_title}</h2>')

                li_tags = ['<ul>']
                for item in items:
                    category = item['category']
                    if category == 'Attachment':
                        li_tags.append(
                            f'<li><a href="{course_name}/{item["title"]}">'
                            f'{self.emoji[category]} {item["title"]}</a></li>'
                        )
                    elif category == 'Context Module Sub Header':
                        if len(li_tags) == 1:
                            li_tags.append(
                                f'<h3>{item["title"]}</h3>'
                            )
                        else:
                            li_tags.append('</ul><ul>')
                            li_tags.append(
                                f'<h3>{item["title"]}</h3>'
                            )
                    else:
                        if 'http' in item['url']:
                            url = item['url']
                        else:
                            url = c.DOMAIN + item['url']

                        li_tags.append(
                            f'<li><a href="{url}">'
                            f'{self.emoji.get(category, f"<b>{category}</b>")}'
                            f' {item["title"]}</a></li>'
                        )

                li_tags.append('</ul>')

                tags.append('\n'.join(li_tags))

            if (FOOL/self.semester).exists():
                pass
            else:
                (FOOL/self.semester).mkdir(parents=True, exist_ok=True)

            (FOOL/self.semester/f'{course_name}.html').write_text(
                self.template(course_name, ''.join(tags)), encoding='utf8'
            )

    def template(self, course_name, string):
        soup = BeautifulSoup(
            '<html><body><div class="main"></div></body></html>',
            'html.parser'
        )
        soup.insert(0, Doctype('html'))
        head = BeautifulSoup(HEAD.read_text(encoding='utf8'), 'html.parser')
        soup.html.insert(0, head)
        NAVBAR = SRC/f'{self.semester}_navbar.html'
        nav = BeautifulSoup(NAVBAR.read_text(encoding='utf8'), 'html.parser')
        # TODO: course html directory may change in future
        active = nav.find('a', href=f'{course_name}.html')
        active['class'] = 'active'
        soup.body.insert(0, nav)
        soup.div.append(BeautifulSoup(string, 'lxml'))

        return soup.prettify()
