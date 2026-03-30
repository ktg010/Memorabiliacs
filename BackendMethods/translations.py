import gettext
import os
import streamlit as st

# Set up gettext
localedir = os.path.join(os.path.dirname(__file__), '..', 'locale')
gettext.bindtextdomain('memorabiliacs', localedir)
gettext.textdomain('memorabiliacs')

# Cache for translations
_translation_cache = {}

def load_translations(lang):
    if lang in _translation_cache:
        return _translation_cache[lang]
    
    po_file = os.path.join(localedir, lang, 'LC_MESSAGES', 'memorabiliacs.po')
    translations = {}
    if os.path.exists(po_file):
        with open(po_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Simple .po parser
        lines = content.split('\n')
        msgid = None
        in_msgstr = False
        msgstr_lines = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('msgid "'):
                if msgid and msgstr_lines:
                    translations[msgid] = ''.join(msgstr_lines)
                msgid = line[7:-1]  # Remove 'msgid "' and '"'
                in_msgstr = False
                msgstr_lines = []
            elif line.startswith('msgstr "'):
                in_msgstr = True
                msgstr_lines.append(line[8:-1])  # Remove 'msgstr "' and '"'
            elif in_msgstr and line.startswith('"') and line.endswith('"'):
                msgstr_lines.append(line[1:-1])  # Remove surrounding quotes
        
        # Last one
        if msgid and msgstr_lines:
            translations[msgid] = ''.join(msgstr_lines)
    
    _translation_cache[lang] = translations
    return translations

# Get current language from session state, default to 'en'
def get_current_lang():
    if 'language' not in st.session_state:
        st.session_state.language = 'en'
    return st.session_state.language

# Set language
def set_language(lang):
    _translation_cache.clear()
    st.session_state.language = lang

# Translation function
def _(s):
    lang = get_current_lang()
    if lang == 'en':
        return s
    translations = load_translations(lang)
    return translations.get(s, s)