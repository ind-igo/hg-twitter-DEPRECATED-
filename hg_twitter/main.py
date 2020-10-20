import tweepy
from ttp import ttp
from google.cloud import storage
from urllib.parse import urlparse, parse_qs
import requests
import os
import time

CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('ACCESS_TOKEN_SECRET')
FILENAME = 'last_seen_id.txt'

auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)
p = ttp.Parser()

def get_last_seen_id(filename):
  if os.path.getsize(filename) == 0: return 0
  with open(filename, 'r') as f:
    last_seen_id = int(f.read().strip())
    return last_seen_id

def store_last_seen_id(id, filename):
  with open(filename, 'w') as f:
    f.write(str(id))
  return

def get_id(parsed_url):
  quer_v = parse_qs(parsed_url.query).get('v')
  if quer_v:
    return quer_v[0]
  pth = parsed_url.path.split('/')
  if pth:
    return pth[-1]

def form_reply(reciever_name, video_ids):
  reply = '@' + reciever_name + ' Here is a readable transcription of your video:'
  for id in video_ids:
    reply += ' https://hierogly.ph/transcribe?v=' + id
  return reply

def reply_to_tweets():
  last_seen_id = get_last_seen_id(FILENAME)
  mentions = api.mentions_timeline(last_seen_id, tweet_mode='extended')

  for mention in reversed(mentions):
    print(str(mention.id) + ' - ' + mention.full_text)
    store_last_seen_id(last_seen_id, FILENAME)
    if 'transcribe' not in mention.full_text:
      print('This tweet does not contain the word "transcribe"')
      continue

    # Grab Youtube links in parent
    parent = mention.in_reply_to_status_id
    result = p.parse(api.get_status(parent).text)
    if not result.urls:
      print('There are no links in the parent tweet')
      continue

    video_id_list = []
    for url in result.urls:
      redirect = requests.get(url).url
      parsed = urlparse(redirect)
      if parsed.netloc == 'www.youtube.com' or parsed.netloc == 'youtu.be':
        video_id = get_id(parsed)
        video_id_list.append(video_id)
      else:
        print('Links in parent tweet are not Youtube links')
        continue

    if not video_id_list:
      print('Links in parent tweet are not Youtube links')
      continue

    # Make Hieroglyph cache transcripts
    for vid in video_id_list:
      requests.get('https://hierogly.ph/api/transcribe?v='+vid)

    # Reply with Hieroglyph link
    reply = form_reply(mention.user.screen_name, video_id_list)
    api.update_status(reply, mention.id)

if __name__ == "__main__":
  reply_to_tweets()