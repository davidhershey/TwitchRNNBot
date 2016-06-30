import urllib
import os
import json

if not os.path.exists('./emotes'):
    os.makedirs('./emotes')
print('Saving emotes to folder: ' + os.path.abspath('./emotes') + '...')
print('Grabbing emote list...')
emotes = json.load(urllib.urlopen('https://twitchemotes.com/api_cache/v2/global.json'))
for code, emote in emotes['emotes'].items():
    print('Downloading: ' + code + '...')
    url = emotes['template']['large'].replace('{image_id}', str(emote['image_id']))
    img='./emotes/' + code + '.png'
    print url,img
    urllib.urlretrieve(url,img)
print('Done! Kappa')
