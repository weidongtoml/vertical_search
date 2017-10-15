from bs4 import BeautifulSoup
import os
import hashlib
import pymongo
import time

BASE_URL = 'https://gogodramaonline.com'
DATA_FILE_DIR = './data'

def retrieveFromUrl(url, local_file):
    if not os.path.isdir(DATA_FILE_DIR):
        os.mkdir(DATA_FILE_DIR)

    local_path = DATA_FILE_DIR + '/' + local_file

    if not os.path.isfile(local_path):
        # this is to work around urllib.urlopen failed to download over https
        os.system('wget %s -O %s' % (BASE_URL + '/' + url, local_path))
    return open(local_path, encoding='utf-8').read()

def do_hash(content):
    m = hashlib.sha256()
    m.update(bytes(content, 'utf-8'))
    return m.hexdigest()[:32]


def get_list_of_drama():
    DRAMA_INDEX_URL = 'drama.html'
    DRAMA_LIST_FILE = './drama.html'

    index_content = retrieveFromUrl(DRAMA_INDEX_URL, DRAMA_LIST_FILE)
    soup = BeautifulSoup(index_content, 'html.parser')
    drama_names_and_urls = [{'href': lnk.attrs['href'], 'title': lnk.attrs['title']}
                            for lnk in soup.find(class_='drama_list_body').find_all('a')
                            if 'title' in lnk.attrs]
    #print(drama_names_and_urls)

    return drama_names_and_urls


def get_video_links(video_name, watch_video_page_url):
    pass
    # looks like we might need to use headless browser to retrieve the video link instead
    #
    # name_hash = do_hash(video_name)
    # watch_video_page = retrieveFromUrl(watch_video_page_url, 'watch-video-' + name_hash)
    # soup = BeautifulSoup(watch_video_page, 'html.parser')
    # iframe_url = 'http:' + soup.find(class_='anime_video_body_watch').find(class_='anime_video_body_watch_items load upload').find('iframe').attrs['src']
    # print('downloading from ' + iframe_url)
    # primary_video_page = retrieveFromUrl(iframe_url, 'video-1-' + name_hash)
    # soup2 = BeautifulSoup(primary_video_page, 'html.parser')
    # video_url = soup2.find('video').attr['src']
    # print(video_url)
    #
    # pass


def get_drama_meta_data(drama):
    drama_overview_page = retrieveFromUrl(drama['href'], 'drama-' + do_hash(drama['title']))
    soup = BeautifulSoup(drama_overview_page, 'html.parser')
    drama_info_body = soup.find(class_='drama_info_body')

    drama_meta = {
        'Title': drama['title']
    }

    drama_meta['ImageUrl'] = drama_info_body.find(class_='info_left').find('img').attrs['src']

    drama_meta['Description'] = drama_info_body.find(class_='info_des').string


    meta_info = drama_info_body.find(class_='des')
    if meta_info:
        for meta in meta_info.find_all(class_='type'):
            field_name = meta.span.string.strip()[:-1]
            if field_name in ['Country', 'Type', 'Status', 'Released']:
                drama_meta[field_name] = meta.contents[1].string.strip() if len(meta.contents) > 1 else ''
            else:
                drama_meta[field_name] = [v.strip() for v in meta.contents[1].string.strip().split(',')] if len(meta.contents) > 1 else []

    episodes = []
    episode_links = drama_info_body.find(class_='drama_info_episodes_next')
    if episode_links:
        for esp in episode_links.find_all('a'):
            esp_name = esp.string
            esp_url = esp.attrs['href']
            episodes.append({
                'Name': esp_name,
                'Url': esp_url
            })
            get_video_links(esp_name, esp_url)

    drama_meta['Episodes'] = episodes

    return drama_meta


def get_db_collection():
    client = pymongo.MongoClient()
    db = client.video_db
    return db.gogo_drama


def is_drama_in_db(db_collection, drama_name):
    return db_collection.find({'Title': drama_name}).count() > 0


def store_meta(db_collection, meta_data):
    inserted_id = db_collection.insert_one(meta_data).inserted_id
    print(meta_data['Title'], inserted_id)


def crawl():
    drama_list = get_list_of_drama()

    db_collection = get_db_collection()

    for drama in drama_list:
        if not is_drama_in_db(db_collection, drama['title']):
            meta_data = get_drama_meta_data(drama)
            store_meta(db_collection, meta_data)
            time.sleep(0.3)
        else:
            print('Skipping: ', drama['title'])

if __name__ == '__main__':
    # start mongoDB first
    # mongod --config /usr/local/etc/mongod.conf
    #
    crawl()