from flask import Flask
from threading import Thread
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
from flask import request

app = Flask('')
chrome_options = Options()
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--headless')
driver = webdriver.Chrome(options=chrome_options)

port = 8080


def run():
    app.run(host='0.0.0.0', port=port)


def keep_alive():
    t = Thread(target=run)
    t.start()


# BODY: { url: '@DavidBombai', maxCount: 1000}
@app.route('/scrape', methods=['POST'])
def question():
    videos_to_export = []
    channel_data = {
        "channelURL": "",
        "channelName": "",
        "videos_count": 0,
        "videos": videos_to_export
    }
    # request.form to get form parameter
    if request.method == 'POST':
        content = request.json
        url = str(content['url'])
        maxCount = int(str(content['maxCount']))
        if maxCount == 0:
            maxCount = 100000
        url = "https://m.youtube.com/" + url + "/videos"
        print(str(url))

        channel_data["channelURL"] = url
        driver.get("https://m.youtube.com/?persist_app=1&app=m")
        driver.get(url)

        WebDriverWait(driver, 60).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@class='compact-media-item']")))
        sleep(5)

        channel_data["channelName"] = driver.find_element(
            By.XPATH, "//h1[@class='c4-tabbed-header-title']").text

        videos = driver.find_elements(By.XPATH,
                                      "//div[@class='compact-media-item']")
        i = 0
        count_of_videos = len(videos)
        scroll = 0
        while i < 20 and maxCount > count_of_videos:
            scroll += 1
            i += 1
            driver.execute_script("window.scrollTo(0, " + str((200 * scroll)) +
                                  ")")
            sleep(0.1)
            videos = driver.find_elements(
                By.XPATH, "//div[@class='compact-media-item']")
            print("///Scrolling///")
            if len(videos) > count_of_videos:
                print("Keep scrolling...")
                count_of_videos = len(videos)
                i -= 15
                sleep(2)

        videos = driver.find_elements(By.XPATH,
                                      "//div[@class='compact-media-item']")
        for video in videos:
            link_to_video = video.find_element(
                By.XPATH,
                ".//a[@class='compact-media-item-image']").get_attribute(
                    "href")
            title = video.find_element(
                By.XPATH, ".//h4[@class='compact-media-item-headline']").text
            video_obj = {
                "link": link_to_video.split("https://m.youtube.com/")[1],
                "title": title
            }
            videos_to_export.append(video_obj)

        channel_data["videos_count"] = len(videos)
        json_to_post = json.dumps(channel_data)
        print(json_to_post)
    return json.dumps(channel_data)


if __name__ == "__main__":  # Makes sure this is the main process
    run()
