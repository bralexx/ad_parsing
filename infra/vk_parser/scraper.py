import mysql.connector
import json
import requests
import typing as tp
import datetime
from time import sleep

import sys
sys.path.append('../..')
from consts import MY_VK_API_TOKEN as ACCESS_TOKEN

class Scraper:
  def __init__(self):
    self.cnx = mysql.connector.connect(
      host='localhost',
      user='scraper',
      database='vk_scrap'
    )
    self.cursor = self.cnx.cursor()
    headers = {
      "Authorization": f"Bearer {ACCESS_TOKEN}"
    }
    self.params = {
      'v': '5.137'
    }
    self.session = requests.Session()
    self.session.headers.update(headers)
    self.date_limit = int(datetime.datetime(2015, 1, 1, 0, 0, 0).timestamp())
    self.dump_errors = 0
    self.get_errors = 0
    self.posts_batch_size = 100

  def get_unparsed(self):
    query = "select * from walls"
    self.cnx.commit()
    self.cursor.execute(query)
    rows = self.cursor.fetchall()
    return rows
  
  def dump_to_db(self, post_json):
    primary_cols = ['owner_id', 'id', 'date', 'text']
    values = [post_json['owner_id'], post_json['id'], post_json['date'], post_json['text']]
    values.append(json.dumps({key:post_json[key] for key in post_json.keys() if key not in primary_cols}))
    query = "insert into posts (owner_id, id, date, text, other) values (%s, %s, from_unixtime(%s), %s, %s)"
    self.cursor.execute(query, values)
    self.cnx.commit()
  
  def scrap_wall(self, wall_info: tp.Tuple[int, str], offset:int=0):
    request = "https://api.vk.com/method/wall.get?" + (f"domain={wall_info[1]}" if wall_info[1] else f"owner_id={wall_info[0]}")
    request += f"&offset={offset}&count={self.posts_batch_size}"
    response = self.session.get(request, params=self.params)
    return json.loads(response.content)['response']

  def scrap_whole_wall(self, wall_info):
    info = self.scrap_wall(wall_info)
    items = info['items']
    total = info['count']
    count = 0
    while count < total and items[0]['date'] > self.date_limit:
      if self.get_errors > 1000 or self.dump_errors > 1000:
        print('get errors: ', self.get_errors)
        print('dump errors: ', self.dump_errors)
        self.get_errors = 0
        self.dump_errors = 0
      try:
        items = self.scrap_wall(wall_info, offset=count)['items']
      except:
        self.get_errors += 1
      for item in items:
        try:
          self.dump_to_db(item)
        except:
          self.dump_errors += 1
      count += len(items)
  
  def mark_parsed(self, wall_info:tp.Tuple[int, str]):
    query = "update walls set is_parsed=true where " + (f"owner_id={wall_info[0]}" if wall_info[0] else f"domain=\"{wall_info[1]}\"")
    self.cursor.execute(query)
    self.cnx.commit()
  
  def scrap_all(self):
    while True:
      walls = self.get_unparsed()
      for wall in walls:
        if not wall[2]:
          print(f'parsing {wall}')
          try:
            self.scrap_whole_wall(wall)
            self.mark_parsed(wall)   
          except:
            pass
      if len(walls) == 0:
        print('start sleep')
        sleep(600)
        print('end sleep')


if __name__ == '__main__':
  print('hi')
  sc = Scraper()
  sc.scrap_all()