# -*- coding: utf-8 -*-
import configparser
import os
import smtplib
import subprocess
import sys
import time
from datetime import datetime, date
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
from enum import Enum
from os.path import basename

try:
    from pip._internal.utils.misc import get_installed_distributions
except ImportError:  # pip<10
    from pip import get_installed_distributions

# TODO: Move for another file of image processing only
# TODO: Remove PIL dependency here
from PIL import Image

# TODO: Move for another file of http requests only
# TODO: Remove urllib3 dependecy here
from urllib3 import disable_warnings

__OUTPUT_LINE_SIZE = 80
__INDENT_SIZE = 4
__COMMA_SPACE = ', '

__today = date.today()
__file_name = os.path.basename(sys.argv[0] if sys.argv[0] else 'dgm_lib.core.utils.py')
__base_dir = os.path.dirname(sys.argv[0] if sys.argv[0] else '.')
__log_dir = os.path.join(__base_dir, 'log', __today.strftime('%Y'), __today.strftime('%m.%b'), __today.strftime('%d'))
__log_file = os.path.join(__log_dir, os.path.basename(__file_name).replace('.py', '_{p}.log'.format(p=os.getpid())))
__database_log_file = __log_file.replace('.log', '_database.log')
__files_dir = os.path.join(__base_dir, 'files', __today.strftime('%Y'), __today.strftime('%b'), __today.strftime('%d'))

print('')
print(str('*' * __OUTPUT_LINE_SIZE))
print('D G M   L I B')
print(str('*' * __OUTPUT_LINE_SIZE))
print('date.............: {d}'.format(d=__today))
print('dir_log..........: {d}'.format(d=__log_dir))
print('base_dir.........: {b}'.format(b=__base_dir))
print('file_log.........: {f}'.format(f=__log_file))
print('file_name........: {f}'.format(f=__file_name))
print('files_directory..: {f}'.format(f=__files_dir))
print('database_log_file: {d}'.format(d=__database_log_file))
print(str('*' * __OUTPUT_LINE_SIZE))
print('')


class LogLevel(Enum):
    debug = 0
    info = 1
    warning = 2
    error = 3
    production = 4


# TODO: Use python standard logging
class LogApplication:
    _level = LogLevel.debug

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value):
        self._level = value


# TODO: Reorganize loggers by level. Create specific methods (info, debug, warning, etc)
def __log(text, indent_level, truncate_file, log_file, break_line, level=LogLevel.debug):
    '''
    Send a text <text> to log file <log_file>.

    :param text: text to be written
    :param indent_level: indent level (used to specify hierarchy)
    :param truncate_file: empty file if true
    :param log_file: the log file it self
    :param break_line: creates a new line if true
    :param level: application level
    '''

    if not os.path.exists(__log_dir):
        print('creating the log directory {d}'.format(d=__log_dir))
        os.makedirs(__log_dir)

    if level < LogApplication.level:
        return

    s = '{h} - [{l}]: '.format(h=str(current_time()), l=level.name.upper())
    if not break_line:
        s += indent_text(text='> {t}'.format(t=text), indent_level=indent_level)
    with open(log_file, 'w' if not break_line and truncate_file else 'a') as f:
        if truncate_file:
            f.write('{a}\n'.format(a=str('*' * __OUTPUT_LINE_SIZE)))
            f.write(justify_text(__file_name.replace('.py', '')).uper().center(__OUTPUT_LINE_SIZE))
            f.write('{a}\n'.format(a=str('*' * __OUTPUT_LINE_SIZE)))

    try:
        print(s)
    except Exception:
        print(s.encode(sys.stdout.encoding, errors='ignore'))


def __error(msg, exception, indent_level, finish, driver, db):
    '''
    Default error msg. log on file and takes a screenshot (selenium only)

    :param msg: Message to be logged
    :param exception: Exception catched
    :param indent_level: indent level (used to specify hierarchy)
    :param driver: (selenium only) used web driver
    :param finish: should end processing?
    :param db: is a database error?
    '''

    log_function = database_log if db else log

    log_function(text=msg, indent_level=indent_level, level=LogLevel.error)
    if exception:
        log_function(text='Reason: {e}'.format(e=exception), indent_level=indent_level + 1, level=LogLevel.error)
    if driver:
        take_screenshot_webdriver(driver, 'ERROR - {f}_{d}.png'.format(f=__file_name, d=now()))
    if finish:
        terminate_processing(error=msg)


def log_empty_line(level: LogLevel = LogLevel.debug):
    __log(text='', indent_level=0, truncate_file=False, log_file=__log_file, break_line=True, level=level)


# TODO: Move to database utils
def database_log_empty_line(level: LogLevel = LogLevel.debug):
    __log(text='', indent_level=0, truncate_file=False, log_file=__database_log_file, break_line=True, level=level)


def log(text, indent_level=0, truncate_file=False, level: LogLevel = LogLevel.debug):
    __log(text=text, indent_level=indent_level, truncate_file=truncate_file, log_file=__log_file, break_line=False,
          level=level)


# TODO: Move to database utils
def database_log(text, indent_level=0, truncate_file=False, level: LogLevel = LogLevel.debug):
    __log(text=text, indent_level=indent_level, truncate_file=truncate_file, log_file=__database_log_file,
          break_line=False, level=level)


# TODO:Extend on selenium utils; Remove driver parameter here
def error(msg, exception=None, indent_level=0, finish=True, driver=None):
    __error(msg=msg, exception=exception, indent_level=indent_level, finish=finish, driver=driver, db=False)


# TODO:Extend on selenium utils; Remove driver parameter here
def database_error(msg, exception=None, indent_level=0, finish=True, driver=None):
    __error(msg=msg, exception=exception, indent_level=indent_level, finish=finish, driver=driver, db=True)


def now(fmt='%Y-%m-%d %H:%M:%S'):
    '''
    Return current datetime in specified format

    :param fmt: desired format
    :return: current datetime in specified format
    '''

    return str(datetime.now().strftime(fmt))


def indent_text(text, indent_level=0):
    '''
    insert blank spaces before text start to indent them

    :param text: text to be indented
    :param indent_level: hierarchical log message level
    :return: indented text
    '''

    indent = ' ' * __INDENT_SIZE
    result = ''
    for i in range(indent_level):
        result += indent
    result += text
    return result


def space_text(text, space_character=' '):
    '''
    Creates a new text adding the char <space_character> between each char of text <text>

    :param text: text to be spaced
    :param space_character: character to be inserted between text
    :return: new text with <space_character> merged between <text>
    '''

    s = ''
    for i in str(text):
        s += '{t}{c}'.format(t=i, c=space_character)
    return s.rstrip()


# TODO: Move for selenium utils
def take_screenshot_webdriver(driver, filename: str = None):
    '''
    Saves a webdriver screenshot in specified filename

    :param driver: instance of webdriver
    :param filename: path for new image file
    '''

    file = filename if filename else os.path.join(__base_dir, 'screenshot', now('%'))
    if not os.path.exists(os.path.dirname(file)):
        os.makedirs(os.path.dirname(file))
    driver.get_screenshot_as_file(file)


def send_email(sender: str, to: list, subject: str = '', message: str = '', attachments: list = None,
               server: str = None,
               indent_level=0):
    '''
    Sent a e-mail based on parameters received

    :param sender: e-mail sender
    :param to: e-mail target
    :param subject: e-mail subject
    :param message: e-mail message
    :param attachments: any attachments
    :param server: e-mail SMTP server
    :param indent_level: indent level (for log only)
    :return: True if success, false if not
    '''

    if server and to:
        email_sender = 'DGM.LIB' if not sender else sender
        log(text='Sending e-mail from {f} to {t}'.format(f=email_sender, t=to), indent_level=indent_level,
            level=LogLevel.info)
        log(text='Subject: {s}'.format(s=subject), indent_level=indent_level + 1, level=LogLevel.info)
        log(text='Attachments: {a}'.format(a='Yes' if attachments else 'No'), indent_level=indent_level + 1,
            level=LogLevel.info)

        msg = MIMEMultipart()
        msg['From'] = email_sender
        msg['To'] = __COMMA_SPACE.join(to)
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject

        msg.attach(MIMEText(message))

        for a in attachments or []:
            with open(a, 'rb') as file:
                part = MIMEApplication(file.read(), Name=basename(a))
                part['Content-Disposition'] = 'attachment; filename="{f}"'.format(f=basename(a))
                msg.attach(part)

        try:
            smtp = smtplib.SMTP(server)
            try:
                smtp.sendmail(from_addr=email_sender, to_addrs=to, msg=msg.as_string())
            finally:
                smtp.close()
            log(text='e-mail sent', indent_level=indent_level, level=LogLevel.info)
        except Exception as e:
            error('error sending e-mail', exception=e, indent_level=indent_level)
    else:
        log('E-mail server or destination not found. server={s}, destination={t}'.format(s=server,
                                                                                         t=__COMMA_SPACE.join(to)),
            indent_level=indent_level, level=LogLevel.warning)


def wait(seconds: int, msg: str = '', indent_level=0):
    '''
    Pause the process for <seconds> amount of secs

    :param seconds: amount of time to remain paused
    :param msg: msg to be logged with count
    :param indent_level: hierarchical log message level
    '''

    for s in range(seconds):
        time.sleep(1)
        log(text=msg if msg else '...waiting {s} second(s).'.format(s=s + 1), indent_level=indent_level)


def terminate_processing(error_status):
    '''
    Finish the process with a log message

    :param error_status: text to be add to log
    :return:
    '''

    if not error_status:
        log(text='Process terminated successfully', level=LogLevel.info)
    else:
        error(msg='Error processing.', exception=error_status)
        if isinstance(error_status, int):
            sys.exit(error_status)
        else:
            sys.exit(-1)


def wait_for_file(filename, timeout, indent_level=0):
    '''
    Waits for a specified file for a certain amount of time max
    
    :param filename: full path of filename 
    :param timeout: max timeout
    :param indent_level: hierarchical log message level
    :return: True if found file, false if not 
    '''

    count = 1
    result = False
    while count <= timeout:
        try:
            with open(filename) as file:
                size = os.fstat(file.fileno()).st_size
                wait(seconds=1, msg='size file: {s}'.format(s=size), indent_level=indent_level)
                if size == os.fstat(file.fileno()).st_size:
                    result = True
                    break
        except (FileExistsError, FileNotFoundError):
            wait(seconds=1, msg='file not found yet', indent_level=indent_level)
        count += 1
        if count == timeout:
            error(msg='even after {s} second(s) the file {f} was not found. Wait aborted.'.format(s=time, f=filename),
                  indent_level=indent_level, finish=False)
            break
    return result


def get_environment_variable(variable_name):
    return os.environ[variable_name]


def change_environment_variable(variable_name, value):
    '''
    Change the value of an environment variable

    :param variable_name: name of variable
    :param value: new value
    '''

    log(text='=' * __OUTPUT_LINE_SIZE, level=LogLevel.info)
    log(text='Changing the environment variable {v}'.format(v=variable_name).upper().center(__OUTPUT_LINE_SIZE),
        indent_level=1, level=LogLevel.info)
    log(text='=' * __OUTPUT_LINE_SIZE, level=LogLevel.info)
    log(text='New value: ', indent_level=1)
    log(text=value, indent_level=2)
    if value:
        if variable_name in os.environ:
            log(text='Old value: {o}'.format(o=os.environ[variable_name]), indent_level=1)
            os.environ[variable_name] = value
            log(text='New value: {n}'.format(n=value))
        else:
            log(text='Environment variable {v} not found.'.format(v=variable_name), level=LogLevel.warning)
    else:
        log(text='New value is empty', level=LogLevel.warning)
    log(text='=' * __OUTPUT_LINE_SIZE, level=LogLevel.info)


# TODO: Move to database utils
def change_oracle_home(path):
    '''
    Change path of oracle home of environment variable ORACLE_HOME

    :param path: new path of oracle home
    '''

    if path.find('\\client'):
        change_environment_variable(variable_name='ORACLE_HOME', value=path)
    else:
        log(text='The key word \'client\' was not found on specified path. Changing denied', level=LogLevel.warning)


def get_month_name(date_in_month: date):
    '''
    Return the name of month in portuguese (PT-BR)

    :param date_in_month: date in month
    :return: name of month of <date> in portugues (PT-BR)
    '''

    if date_in_month.month == 1:
        return 'JANEIRO'
    elif date_in_month.month == 2:
        return 'FEVEREIRO'
    elif date_in_month.month == 3:
        return 'MARÇO'
    elif date_in_month.month == 4:
        return 'ABRIL'
    elif date_in_month.month == 5:
        return 'MAIO'
    elif date_in_month.month == 6:
        return 'JUNHO'
    elif date_in_month.month == 7:
        return 'JULHO'
    elif date_in_month.month == 8:
        return 'AGOSTO'
    elif date_in_month.month == 9:
        return 'SETEMBRO'
    elif date_in_month.month == 10:
        return 'OUTUBRO'
    elif date_in_month.month == 11:
        return 'NOVEMBRO'
    elif date_in_month.month == 12:
        return 'DEZEMBRO'
    else:
        return 'INVALID_MONTH'


def execute_command(command):
    '''
    Execute a command line <command> on current operational system and returns the output

    :param command: command line to be executed
    :return: output generated by command line
    '''

    log(text='execute command', level=LogLevel.info)
    output = 'command not executed'
    try:
        output = subprocess.check_output(command, shell=True, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        if e.returncode == 255:
            output = e.output
    return output


def verify_python_installed_package(package_name: str):
    '''
    Verify if a python package is installed on environment

    :param package_name: nome of package
    '''

    return package_name.lower() in [str(package.project_name).lower() for package in get_installed_distributions()]


def get_file_date(file):
    '''
    Return the date of specified <filename>

    :param file: full path of file
    :return: date of file on dd/mm/yyyy format
    '''

    return time.strftime('%d/%m/%Y', time.gmtime(os.path.getmtime(file)))


def verify_day_of_file(file, day=time.time()):
    '''
    Verify if the file <file> is of day <day>

    :param file: full path of a file
    :param day: number of day in month to verify
    :return: True if file is for the day <day>, False if not
    '''

    return False if not os.path.exists(file) else get_file_date(file) == time.strftime('%d/%m/%Y', time.gmtime(day))


# TODO: Move for another file of image processing only
def get_valid_image(image, resize: tuple = (50, 50)):
    '''
    Verify if <image> is a valid image or a path of an image. If resize is specified, the image returned will be resized

    :param image: image (PIL.Image) object or path of a image
    :param resize: new size of the image
    :return: an instance of image object if <image> is valid, else None
    '''

    assert (Image.isImageType(image) or isinstance(image,
                                                   str)), 'Invalid Type. Must be PIL.Image object or path of an image'
    img = image if Image.IsImageType(image) else Image.open(image) if type(image) == str and os.path.isfile(
        image) else None
    if resize:
        img.resize(resize)
    return img


# TODO: Move for another file of image processing only
def get_average_color_of_image(image):
    '''
    Return RGB from the average color of image <image>

    :param image: image (PIL.Image) object or path of a image
    :return: RGB code of average color
    '''

    img = get_valid_image(image=image)
    if img:
        width, height = img.size
        img.convert('RGB')

        r_total, g_total, b_total, count = 0

        for w in range(0, width):
            for h in range(0, height):
                r, g, b = img.getpixel((w, h))
                r_total += r
                g_total += g
                b_total += b
                count += 1

        return r_total / count, g_total / count, b_total / count
    else:
        return None


# TODO: Move for another file of image processing only
def get_percentile_of_colors(image):
    '''
    Return a list of all colors available on image <image>, ordered by most present

    :param image: image (PIL.Image) object or path of a image
    :return: list of all colors available on image <image>, ordered by relevance
    '''

    img = get_valid_image(image=image)
    if img:
        total = sum(color[0] for color in img.getcolors())
        fractions = []
        for color in img.getcolor():
            fractions.append(((color[1][0], color[1][1], color[1][2]), color[0] / total * 100))
        return sorted(fractions, reverse=True)
    else:
        None


# TODO: Move for another file of image processing only
def get_percentile_of_specific_color(image, rgb_color: tuple):
    '''
    Return a list of all colors available on image <image>, ordered by most present

    :param image: image (PIL.Image) object or path of a image
    :param rgb_color: RGB code of a color
    :return: list of all colors available on image <image>, ordered by relevance
    '''

    return sum(color[1] for color in get_percentile_of_colors(image=image) if color[0] == rgb_color) if get_valid_image(
        image=image) else None


# TODO: Move for another file of image processing only
def get_percentile_of_white(image):
    '''
    Return the percentile of white color on specified image

    :param image: image (PIL.Image) object or path of a image
    :return: percentile of white color on specified image
    '''

    return get_percentile_of_specific_color(image=image, rgb_color=(255, 255, 255)) if get_valid_image(
        image=image) else None


# TODO: Move for another file of image processing only
def get_count_colors(image: Image):
    '''
    Return quantity of different colors present on specified image <image>
    :param image: image (PIL.Image) object or path of a image
    :return: quantity of different colors present on specified image <image>
    '''

    img = get_valid_image(image=image)
    return len(img.getcolors()) if img else None


def get_normalized_url(url: str):
    '''
    Normalize a url. Remove duplicated back slash

    :param url: url to be adjusted
    :return: normalized url
    '''

    segments = url.split('/')
    correct_segments = []
    for segment in segments:
        if segment:
            correct_segments.append(segment)
    first_segment = str(correct_segments[0])
    if first_segment.find('http') == -1:
        correct_segments = ['http:'] + correct_segments
    correct_segments[0] = correct_segments[0] + '/'
    return '/'.join(correct_segments)


# TODO: Move for another file of http requests only
if verify_python_installed_package('eventlet'):
    import eventlet
if verify_python_installed_package('requests'):
    from requests import sessions, get, Response


# TODO: Move for another file of http requests only
def make_request(url, params: str = None, timeout: int = 2, method: str = 'GET', auth: tuple = None,
                 headers: dict = None):
    '''
    Make a http request

    :param url: url to be requested
    :param params: params of method
    :param timeout: max timeout
    :param method: HTTP method
    :param auth: tuple for authentication (user, password)
    :param headers: headers to be added to request
    :return: HTTP response code or, 0 for missing dependencies, -1 for timeout or -2 for any other exception
    '''

    if not verify_python_installed_package('eventlet') or not verify_python_installed_package('requests'):
        error(msg='Missing dependencies. Must have \'eventlet\' and \'requests\'', finish=True)
        return 0, None
    else:
        url = get_normalized_url(url)
        disable_warnings()
        with eventlet.Timeout(timeout):
            result = Response()
            try:
                try:
                    result = get(url=url, params=params, verify=False, auth=auth, headers=headers)
                except eventlet.Timeout:
                    result = None
                    result.status_code = -1
                except Exception as e:
                    result = None
                    result.status_code = -2
                    error(msg='HTTP request exception', exception=e)
            finally:
                return result.status_code, result


# TODO: Move for another file of http requests only
# TODO: Create a enum for protocol (http or https). In future, tcp, ftp, sftp, etc...
def get_new_url(host: str, port: str, resource: str, protocol: str=None):
    '''
    Return a new url based on specified params

    :param host: ip, dns, domain or hostname
    :param port: port. If not specified the new url will https and with no port on it
    :param resource: query string of url
    :param protocol: http or https
    :return: brand new url
    '''

    if port:
        protocol = ('https' if port in ['8443', '443'] else 'http') if not protocol else protocol
        return '{pr}://{h}:{po}/{r}'.format(pr=protocol, h=host, po=port, r=resource)
    else:
        return '{p}://{h}/{r}'.format(p=protocol, h=host, r=resource)


def get_ini_value(filename: str, section: str, option: str, default: str='', encode:str= 'UTF-8'):
    '''
    Gets a value of an option of a section of a configuration ini file (.ini)

    :param filename: full path of ini file
    :param section: section to be found
    :param option: option to get value
    :param default: default value for <option> if not found
    :param encode: encoding to open file
    :return: value of specified option in specified section of specified ini file
    '''

    config = configparser.RawConfigParser()
    config.read(filename, encoding=encode)
    return config.get(section=section, option=option, fallback=default)


def get_normalized_duplicated_chars(text):
    double_chars = {
        '[':']',
        '{':'}',
        '(':')',
    }

    stack = []
    for (i, char) in enumerate(text):
        if char in double_chars.keys():
            stack.append({'idx': i, 'char': char})
        if char in double_chars.values():
            if stack and stack[-1]['char'] == list(double_chars)[list(double_chars.values()).index(char)]:
                stack.pop()
            else:
                stack.append({'idx': i, 'char': char})

    result = text
    for (i, s) in enumerate(stack):
        result = result[:int(s['idx']) - i] + result[int(s['idx'] - i + 1):]

    return result


def singleton(cls, *args, **kw):
    instances = {}

    def _singleton():
        if cls not in instances:
            instances[cls] = cls(*args, **kw)
        return instances[cls]

    return _singleton

if __name__ == '__main__':
    print('module dgm_lib.core.utils called')
