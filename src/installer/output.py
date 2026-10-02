"""Small, log-friendly installer messages; subprocess output stays visible."""
import os
import sys


def message(label, text, *, color='36', error=False):
    stream = sys.stderr if error else sys.stdout
    styled = stream.isatty() and 'NO_COLOR' not in os.environ and os.environ.get('TERM') != 'dumb'
    tag = f'\033[{color}m{label}\033[0m' if styled else label
    print(f'  {tag}' + (f'  {text}' if text else ''), file=stream, flush=True)


def section(title):
    print(flush=True)
    message(title, '', color='1')


def detail(label, value):
    print(f'    {label}: {value}', flush=True)
