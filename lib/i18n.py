"""Shared, process-local UI language; generated project instructions stay English."""
import sys

_language = 'en'


def set_language(lang):
    """Set sv/en explicitly. Invalid values never silently change the language."""
    if lang not in ('sv', 'en'):
        raise ValueError('Language must be sv or en / Språk måste vara sv eller en')
    global _language
    _language = lang
    return lang


def get_language():
    return _language


def tr(sv, en):
    """Select an explicit translation, before formatting any placeholders."""
    return sv if _language == 'sv' else en


def select_language(explicit=None):
    """Ask on every interactive startup; explicit/noninteractive calls never ask."""
    if explicit is not None:
        return set_language(explicit)
    if not sys.stdin.isatty():
        return set_language('en')
    print('Välj språk / Select language:\n  1) Svenska\n  2) English', flush=True)
    while True:
        answer = input('Språk / Language [2]: ').strip().lower()
        if answer in ('1', 'sv', 'svenska'):
            return set_language('sv')
        if answer in ('', '2', 'en', 'english'):
            return set_language('en')
        print('Välj 1 eller 2 / Choose 1 or 2.', flush=True)
