from selenium import webdriver
import crawler
from pymongo import ReturnDocument
import pprint


def get_episode_video_link(url, browser):
    browser.get(url)
    video_divs = browser.find_elements_by_class_name('anime_video_body_watch_items')
    div = video_divs[0]
    if div.get_attribute('class') == 'anime_video_body_watch_items load upload':
        frame = div.find_element_by_tag_name('iframe')
        browser.switch_to.frame(frame)
        video = browser.find_element_by_tag_name('video')
        source = video.find_elements_by_css_selector('*')[0]
        video_url = source.get_attribute('src')
        print(video_url)
        return video_url
    else:
        return None


def update_links(browser, collection):
    videos = collection.find()
    for video in videos:
        is_video_updated = False
        for episode in video['Episodes']:
            if not 'VideoUrl' in episode.keys():
                is_modified = False
                if not episode['Url'].startswith('http'):
                    episode['Url'] = 'https://gogodramaonline.com' + episode['Url']
                    is_modified = True
                try:
                    video_url = get_episode_video_link(episode['Url'], browser)
                    if video_url:
                        episode['VideoUrl'] = video_url
                        is_modified = True
                except Exception as e:
                    print('Failed to update: ')
                    pprint.pprint(episode)
                    print('Encountered error: ', e)
                if is_modified:
                    updated_video = collection.find_one_and_replace({'_id': video['_id']}, video,
                                                            return_document=ReturnDocument.AFTER)
                    is_video_updated = True
        if is_video_updated:
            print('Updated video:', video['Title'])


if __name__ == '__main__':
    browser = webdriver.Chrome()

    collection = crawler.get_db_collection()

    update_links(browser, collection)

    browser.close()
