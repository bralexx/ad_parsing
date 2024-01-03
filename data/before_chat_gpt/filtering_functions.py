import numpy as np
import pandas as pd
import string

import re

import tiktoken

def is_selling_text(text):
    for sub in (r'.*прода[еёю]тся.*', r'.*продажа.*', r'.*прода[юм].*'):
        if re.match(sub, text.lower()) is not None:
            return True
    return False

def is_bad_text(text):
    for sub in (r'.*куп(лю|им).*', r'.*сда(м|ю|дим|ется|ётся).*', r'.*аренд[ау].*', r'.*ищ(у|ем).*', r'.*продан(о|а|ы)?.*'):
        if re.match(sub, text.lower()) is not None:
            return True
    return False

def count_numbers(string):
    string = re.sub(r'([0-9])[.,]([0-9])', r'\1\2', string)
    reg = re.compile('[0-9]+')
    return len(reg.split(string)) - 1

def count_input_tokens(text):
    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    return len(encoding.encode(text))

def count_number_sequences(input_string):
    digit_sequences = re.findall(r'\d+', input_string)
    return len(digit_sequences)

def count_unique_symbols(input_string):
    valid_chars = set(string.ascii_letters + string.digits + string.punctuation + ' ' +
                      'абвгдежзийклмнопрстуфхцчшщъыьэюя' + 'АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')

    count = 0
    for char in input_string:
        if char not in valid_chars:
            count += 1

    return count
