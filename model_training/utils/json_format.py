import json
import re

class JSONProcessor:
  spec_tokens = ["<BOB>", "<EOB>", "<BOT>", "<EOT>", "<BOP>", "<EOP>", "<BOC1>", "<EOC1>", "<BOC2>", "<EOC2>"]
  def process_json(self, json):
    return ''.join([f"<BOB><BOT>{d['Title']}<EOT><BOP>{d['Price']}<EOP><BOC1>{d['Count']}<EOC1><BOC2>{d['Currency']}<EOC2><EOB>" for d in json])

  def unprocess_json(self, s):
    json = []
    for t in re.findall(r'<BOB>(.*?)<EOB>', s):
      try:
        json.append({
          'Title': re.findall(r'<BOT>(.*?)<EOT>', t)[0],
          'Price': re.findall(r'<BOP>(.*?)<EOP>', t)[0],
          'Count': re.findall(r'<BOC1>(.*?)<EOC1>', t)[0],
          'Currency': re.findall(r'<BOC2>(.*?)<EOC2>', t)[0]
        })
      except Exception as e:
        print(t)
        raise e
    return json

default_json_processor = JSONProcessor()
process_json = lambda js: default_json_processor.process_json(js)
unprocess_json = lambda s: default_json_processor.unprocess_json(s)

class SepTokenJSONProcessor:
  spec_tokens = ["<B>", "<T>", "<P>", "<C1>", "<C2>"]
  def process_json(self, json):
    return ''.join([f"<B><T>{d['Title']}<P>{d['Price']}<C1>{d['Count']}<C2>{d['Currency']}" for d in json])

  def unprocess_json(self, s):
    json = []
    for t in s.split('<B>')[1:]:
      try:
        json.append({
          'Title': re.findall(r'<T>(.*?)(<(B|P|C1|C2)>|$)', t)[0][0],
          'Price': re.findall(r'<P>(.*?)(<(T|B|C1|C2)>|$)', t)[0][0],
          'Count': re.findall(r'<C1>(.*?)(<(T|B|P|C2)>|$)', t)[0][0],
          'Currency': re.findall(r'<C2>(.*?)(<(T|B|P|C1)>|$)', t)[0][0]
        })
      except Exception as e:
        print(t)
        raise e
    return json


class TextJSONProcessor:
  spec_tokens = []
  def process_json(self, json):
    return 'Продается: ' + ';'.join([f"{d['Title']} в количестве {d['Count']}, цена {d['Price']} ({d['Currency']})" for d in json])

  def unprocess_json(self, s):
    json = []
    if s.startswith('Продается: '):
      s = s[11:]
    for t in s.split(';'):
      try:
        json.append({
          'Title': re.findall(r'(.*?) в количестве ', t)[0],
          'Count': re.findall(r' в количестве (.*?), цена ', t)[0],
          'Price': re.findall(r', цена (.*?) \(', t)[0],
          'Currency': re.findall(r', цена [^()]*\((.*?)\)(;|$)', t)[0][0]
        })
      except Exception as e:
        print(t)
        raise e
    return json

