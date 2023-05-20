# WORKS AS BOTTER INSTANCE NOT A SERVER, FOR SERVER USE REQUEST_SERVER #

import json
import requests
import re
import time
import asyncio
import aiohttp


class YoutubeScraper:
    def __init__(self, YOUTUBE_CHANNEL_TAG, MAX_COUNT):
        self.API_KEY = ""
        self.NONCE_KEY = ""
        self.BROWSE_ID = ""
        self.MAX_COUNT = MAX_COUNT
        self.YOUTUBE_START_TAG = "hanmlbb7899"  # some shitty video channel with less than 5 videos to just get keys
        self.YOUTUBE_CHANNEL_TAG = YOUTUBE_CHANNEL_TAG  # the channel we want to scrape
        self.real_video_list = []
        self.s = requests.Session()
        self.CONTINUATION_TOKEN = ""
        self.setupCookies()

    def setupCookies(self):
        url = f"https://www.youtube.com/@{self.YOUTUBE_START_TAG}/"
        response = self.s.get(url)
        # response = self.s.request("GET", url, proxies=self.getProxy())
        lang = re.findall('(?<=lang=")[\w]+', response.text)[0].upper()
        try:
            url = "https://consent.youtube.com/save"

            payload = f"gl={lang}&m=false&pc=yt&continue=https://www.youtube.com/@{self.YOUTUBE_START_TAG}?cbrd=1&x=8&v=2&bl={lang.lower()}&hl=en&src=1&set_ytc=true&set_apyt=true&set_eom=false"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Host': 'consent.youtube.com',
            }
            self.s.post(url, data=payload, headers=headers)  # get API KEYS and fill out the FORM
            # self.s.request("POST", url, headers=headers, data=payload, proxies=self.getProxy()) # get API KEYS and fill out the FORM
        except Exception as e:
            print("ok maybe not needed...")

        # response = self.s.request("GET", f"https://www.youtube.com/@{self.YOUTUBE_START_TAG}?cbrd=1", proxies=self.getProxy()) # get other keys
        response = self.s.get(f"https://www.youtube.com/@{self.YOUTUBE_START_TAG}?cbrd=1")  # get other keys

        self.API_KEY = re.findall('(?<=INNERTUBE_API_KEY":")[\w_]+', response.text)[0]
        self.NONCE_KEY = re.findall('(?<=<script nonce=")[\w\-\.]+', response.text)[0]
        self.BROWSE_ID = re.findall('(?<=\"browseId\":\")[\w\-]+', response.text)[0]
        print(self.API_KEY, self.NONCE_KEY, self.BROWSE_ID)


class CustomEncoder(json.JSONEncoder):
    def default(self, o):
        return o.__dict__


class ChannelVideosScraper:

    def __init__(self, scraper: YoutubeScraper):
        self.scraper = scraper

    def firstScrape(self):
        # response = self.s.request("GET", f"https://www.youtube.com/@{self.YOUTUBE_CHANNEL_TAG}/videos", proxies=self.getProxy())
        response = self.scraper.s.get(f"https://www.youtube.com/@{self.scraper.YOUTUBE_CHANNEL_TAG}/videos")
        yt_content_json = re.findall(f'(?<=var ytInitialData = ).+;<\/script>', response.text)[0][:-10]
        yt_content_json = json.loads(yt_content_json)

        videos = yt_content_json["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][1]["tabRenderer"]["content"][
            "richGridRenderer"]["contents"]
        # videos_count = yt_content_json["header"]["c4TabbedHeaderRenderer"]["videosCountText"]["runs"][0]
        # content = yt_content_json["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]["tabRenderer"]["contents"]["sectionListRenderer"]
        #### SOME FUN PART HERE

        for video_index in range(len(videos) - 1):
            video = videos[video_index]
            self.scraper.real_video_list.append(video["richItemRenderer"]["content"]["videoRenderer"])
        try:
            self.scraper.CONTINUATION_TOKEN = \
                videos[len(videos) - 1]["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"][
                    "token"]
            return True
        except:
            return False

    def scrapeVideosDeeper(self):
        self.scraper.s.headers["Content-Type"] = "application/json"
        payload = '{"context":{"client":{"clientName":"WEB","clientVersion":"2.20230206.06.00","platform":"DESKTOP"}}, "browseId":"' + self.scraper.BROWSE_ID + '", "params": "' + self.scraper.NONCE_KEY + '", "continuation": "' + self.scraper.CONTINUATION_TOKEN + '"}'
        # response = self.s.request("POST", "https://www.youtube.com/youtubei/v1/browse?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8&prettyPrint=false", data=payload, proxies=self.getProxy())
        response = self.scraper.s.post(
            f"https://www.youtube.com/youtubei/v1/browse?key={self.scraper.API_KEY}&prettyPrint=false", data=payload)

        yt_content_json = json.loads(response.text)
        videos = yt_content_json["onResponseReceivedActions"][0]["appendContinuationItemsAction"]["continuationItems"]

        for video_index in range(len(videos) - 1):
            video = videos[video_index]
            self.scraper.real_video_list.append(video["richItemRenderer"]["content"]["videoRenderer"])
        if 'continuationItemRenderer' not in videos[len(videos) - 1]:
            print(f"SCRAPED {len(self.scraper.real_video_list)} videos from channel {self.scraper.YOUTUBE_CHANNEL_TAG}")
            return
        self.scraper.CONTINUATION_TOKEN = \
            videos[len(videos) - 1]["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"]
        if len(self.scraper.real_video_list) <= self.scraper.MAX_COUNT:
            time.sleep(0.1)
            self.scrapeVideosDeeper()

    async def scrapeAndSaveResults(self):
        st = time.time()
        moreToScrape = self.firstScrape()
        if moreToScrape:
            self.scrapeVideosDeeper()

        video_list_to_save_to_file = []
        for video in self.scraper.real_video_list:
            video_id = video["videoId"]
            video_title = video["title"]["runs"][0]["text"]
            link_to_video = 'https://www.youtube.com/watch?v=' + video_id
            video_obj = {"link": link_to_video, "title": video_title, "channelTag": self.scraper.YOUTUBE_CHANNEL_TAG}
            video_list_to_save_to_file.append(video_obj)
        videos_arr = await self.check_async_video(video_list_to_save_to_file)

        f = open(f"channels/@{self.scraper.YOUTUBE_CHANNEL_TAG}.txt", "w")
        f.write(json.dumps(videos_arr, indent=2, default=str))
        f.close()

        et = time.time()
        elapsed_time = et - st
        print('Execution time:', elapsed_time, f'seconds, scraped {len(self.scraper.real_video_list)} videos')

    async def fetch_video_info(self, video, session):
        resp = ""
        link_to_video = video["link"]
        title = video["title"]
        try:
            async with session.get(url=link_to_video) as response:
                resp = await response.text()
                print("Successfully got url {} with resp of length {}.".format(link_to_video, len(resp)))
                video_html = str(resp.encode('utf-8'))
                resp = video_html
                video_tags = re.findall(r'(?<=<meta name="keywords" content=")[\w ,#\.\,]+', video_html)[0]
                thumbnail = re.findall(r'(?<=<link itemprop="thumbnailUrl" href=")[\/\w\:\.]+', video_html)[0]
                video_genre = re.findall(r'(?<=<meta itemprop="genre" content=")[\/\w\:\.]+', video_html)[0]
                video_publish_date = \
                    re.findall(r'(?<=<meta itemprop="datePublished" content=")[\/\w\:\.-]+', video_html)[0]
                video_desc = re.findall(r'(?<="shortDescription":").*?"', video_html)[0]
                video_length = re.findall(r'(?<=,"lengthSeconds":")\d+', video_html)[0]
                video_views = re.findall(r'(?<=<meta itemprop="interactionCount" content=")\d+', video_html)[0]
                video_obj = {
                    "link": link_to_video.split("https://www.youtube.com/")[1],
                    "title": title,
                    "tags": str(video_tags),
                    "scraped_at": time.time(),
                    "genre": video_genre,
                    "views": video_views,
                    "desc": video_desc,
                    "lengthSeconds": video_length,
                    "uploadDate": str(video_publish_date),
                    "thumbnail_url": str(thumbnail)
                }
            return video_obj

        except Exception as e:
            print("Unable to get url {} due to {}. RETRYING...".format(link_to_video, e.__class__))
            with open("/var/www/html/selenium_bot/channels_failed/" + video["channelTag"] + ".txt", "a") as f:
                f.write('Unable to get url {} due to {}.\n'.format(link_to_video, e.__class__))
                f.write(resp)
                f.write('\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n')
            while True:
                try:
                    video_obj = self.fetch_video_info(video, session)
                    return video_obj
                except:
                    print("Unable to get url {} RETRYING...".format(link_to_video))

    async def check_async_video(self, videos):
        videos_arr = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            for video in videos:
                tasks.append(asyncio.create_task(self.fetch_video_info(video, session)))
            videos_arr = await asyncio.gather(*tasks)
            #videos_arr = await asyncio.gather(*[self.fetch_video_info(video, session) for video in videos])
        print("Finalized all. Return is a list of len {} outputs.".format(len(videos_arr)))
        return videos_arr


class Comment:
    def __init__(self, who_wrote, content, object=None):
        self.commentContent = content
        self.whoWrote = who_wrote
        self.object = json.dumps(object, indent=2)
        self.category = ""


class VideoCommentsScraper:

    def __init__(self, scraper: YoutubeScraper, video_link):
        self.scraper = scraper
        self.video_link = video_link
        self.video_info = {}
        self.channel_info = {}
        self.comments = []
        self.CONTINUATION_TOKEN = ""

    def firstScrape(self):
        response = self.scraper.s.get(f"https://www.youtube.com/watch?v={self.video_link}")
        yt_content_json = re.findall(f'(?<=var ytInitialData = ).+;<\/script>', response.text)[0][:-10]
        yt_content_json = json.loads(yt_content_json)
        yt_content_json = yt_content_json["contents"]["twoColumnWatchNextResults"]["results"]["results"]["contents"]

        self.video_info = yt_content_json[0]["videoPrimaryInfoRenderer"]
        self.channel_info = yt_content_json[1]["videoSecondaryInfoRenderer"]
        commentsObject = yt_content_json[len(yt_content_json) - 2]["itemSectionRenderer"]["contents"][0][
            "commentsEntryPointHeaderRenderer"]
        # commentsCount = commentsObject["commentCount"]["simpleText"]
        try:
            self.comments.append(Comment(
                commentsObject["contentRenderer"]["commentsEntryPointTeaserRenderer"]["teaserAvatar"]["accessibility"][
                    "accessibilityData"]["label"],
                commentsObject["contentRenderer"]["commentsEntryPointTeaserRenderer"]["teaserContent"]["simpleText"]
            ))
        except:
            print("ok, changed")
        self.CONTINUATION_TOKEN = \
        yt_content_json[len(yt_content_json) - 1]["itemSectionRenderer"]["contents"][0]["continuationItemRenderer"][
            "continuationEndpoint"]["continuationCommand"]["token"]
        return True

    def scrapeDeeper(self, after_first=False):
        self.scraper.s.headers["Content-Type"] = "application/json"
        payload = '{"context":{"client":{"clientName":"WEB","clientVersion":"2.20230206.06.00","platform":"DESKTOP"}}, "browseId":"' + self.scraper.BROWSE_ID + '", "params": "' + self.scraper.NONCE_KEY + '", "continuation": "' + self.CONTINUATION_TOKEN + '"}'
        # response = self.s.request("POST", "https://www.youtube.com/youtubei/v1/browse?key=AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8&prettyPrint=false", data=payload, proxies=self.getProxy())
        response = self.scraper.s.post(
            f"https://www.youtube.com/youtubei/v1/next?key={self.scraper.API_KEY}&prettyPrint=false", data=payload)

        yt_content_json = json.loads(response.text)
        comments = {}
        foundContinuation = False
        try:
            if after_first is True:
                comments = yt_content_json["onResponseReceivedEndpoints"][0]["appendContinuationItemsAction"][
                    "continuationItems"]
            else:
                comments = yt_content_json["onResponseReceivedEndpoints"][1]["reloadContinuationItemsCommand"][
                    "continuationItems"]
        except:
            foundContinuation = False
        i = 0
        for comment in comments:
            i += 1
            if "continuationItemRenderer" in comment:
                foundContinuation = True
                self.CONTINUATION_TOKEN = \
                comment["continuationItemRenderer"]["continuationEndpoint"]["continuationCommand"]["token"]
                continue
            comment_segments = comment["commentThreadRenderer"]["comment"]["commentRenderer"]["contentText"]["runs"]
            whole_comment_content = ""
            for segment in comment_segments:
                whole_comment_content += (segment["text"] + "  ")
            whole_comment_content = whole_comment_content[:-1]
            self.comments.append(
                Comment(comment["commentThreadRenderer"]["comment"]["commentRenderer"]["authorText"]["simpleText"],
                        whole_comment_content,
                        comment["commentThreadRenderer"]["comment"]["commentRenderer"]))
        if foundContinuation:
            self.scrapeDeeper(True)
        else:
            print("Ok, scraped all..")


video_id = "hnczfA8nfBs"
min_length = 75

start_time = time.time()
main_scraper = YoutubeScraper("davidbombal", 10000)
videosScraper = ChannelVideosScraper(scraper=main_scraper)
asyncio.run(videosScraper.scrapeAndSaveResults())
comments_scraper = VideoCommentsScraper(main_scraper, video_id)  #
comments_scraper.firstScrape()
comments_scraper.scrapeDeeper()

for comment in comments_scraper.comments:
    prompt = comment.commentContent
    prompt = re.sub(r'[^\x00-\x7F]+', ' ', prompt)
    prompt = re.sub(r'\s+', ' ', prompt)
    if len(prompt) < min_length:
        continue

output_file = open("output.txt", "w")
toRemove = []
howManyGoodComments = 0
for comment in comments_scraper.comments:
    prompt = comment.commentContent
    prompt = re.sub(r'[^\x00-\x7F]+', ' ', prompt)
    prompt = re.sub(r'\s+', ' ', prompt)
    prompt = prompt.replace(',', '').replace('\"', '').replace('\.', ' ').replace('\n', '').replace('\r', '').replace(
        '\t', '').replace('  ', '').replace('?', '').strip().lower()
    if len(prompt) < min_length:
        toRemove.append(comment)
        continue
    if comment.object is None:
        toRemove.append(comment)
        continue
    resp = requests.post("http://164.92.244.118:5000/api", headers={"Content-Type": "application/json"},
                         data=json.dumps({"prompt": prompt}))
    resp = json.loads(resp.text)
    comment.category = resp["category"]
    output_file.write(resp["category"] + "," + resp["prompt"] + "\n")
    howManyGoodComments += 1
output_file.close()

for comment in toRemove:
    comments_scraper.comments.remove(comment)
print(f"Found {howManyGoodComments} good comments...")

print("Overall --- %s seconds ---" % (time.time() - start_time))
