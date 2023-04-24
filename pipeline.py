import csv
import os
import sys
import argparse
import subprocess
import glob
import shutil
import random
import http.client
import httplib2
import json

import time
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from selenium_pro import webdriver
from selenium_pro.webdriver.common.by import By
from selenium_pro.webdriver.common.keys import Keys

### Define variable ###

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

DATA_STATUS_WATERMARK = "Failed to watermarking video"
DATA_STATUS_WRITE = "Failed to writing metadata"
DATA_STATUS_UPLOAD = "Failed to uploading video"
DATA_STATUS_DONE = "Done"
DATA_HEADER = ['source', 'name', 'title', 'description', 'keywords', 'status']

ENV_GEN_DIR = os.path.join(BASE_PATH, ".gen")
ENV_CONF_DIR = os.path.join(BASE_PATH, ".conf")
ENV_DATA_FILE = os.path.join(BASE_PATH, "vdata.csv")
ENV_TEMPLATE_DESCRIPTION_FILE = os.path.join(ENV_CONF_DIR, "description.tmpl")
ENV_TEMPLATE_KEYWORDS_FILE = os.path.join(ENV_CONF_DIR, "keywords.tmpl")
ENV_WATERMARK_IMAGE_FILE = os.path.join(ENV_CONF_DIR, "watermark.png")
ENV_LOCKED_FILE = os.path.join(ENV_CONF_DIR, ".lock")
ENV_LOGIN_COOKIES_FILE = os.path.join(ENV_CONF_DIR, "login.json")
ENV_CHROMEDRIVER_FILE = os.path.join(ENV_CONF_DIR, "chromedriver.exe")

METADATA_GENERATED_PATH_FORMAT = os.path.join(ENV_GEN_DIR, "{OUTPUT_NAME} -- metadata.csv")
METADATA_HEADER = ['id', 'file_dir', 'filename', 'title', 'description', 'keywords', 'privacy_status', 'watermarked', 'youtube_id']
METADATA_PRIVACY_STATUS = "public"
METADATA_WATERMARKED = "Done"

FFMPEG_BIN_PATH = "ffmpeg"

# Initialize it first before use.
ENV_CLIENT_SECRETS_FILE = None


# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
  http.client.IncompleteRead, http.client.ImproperConnectionState,
  http.client.CannotSendRequest, http.client.CannotSendHeader,
  http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

### Video API ###
def get_secret_id():
    for file in os.listdir(ENV_CONF_DIR):
        if file.endswith(".json") and file.startswith("client_secret_"):
            selected_id = os.path.join(ENV_CONF_DIR, file)
            printout(f"CLIENT_SECRETS_ID : {selected_id}")
            return selected_id

    for file in os.listdir(BASE_PATH):
        if file.endswith(".json") and file.startswith("client_secret_"):
            src = os.path.join(BASE_PATH, file)
            dst = os.path.join(ENV_CONF_DIR, file)
            shutil.move(src, dst)
            printout(f"CLIENT_SECRETS_ID : {dst}")
            return dst
        

def output_video_list(title, youtube_id):
    output_name = 'uploaded_video_link.txt' 
    file = open(output_name,'a')
    file.write( datetime.now().strftime('%Y-%m-%d %H:%M:%S') +' , '+title+' , '+'https://youtu.be/'+youtube_id+'\n')
    file.close()

def initialize_upload(youtube, video_file, video_title, video_category, video_description, video_keywords, video_privacy_status, video_is_for_kids):
    tags = None
    if video_keywords:
        tags = video_keywords.split(",")

    body=dict(
        snippet=dict(
            title=video_title,
            description=video_description,
            tags=tags,
            categoryId=video_category
        ),
        status=dict(
            privacyStatus=video_privacy_status,
            selfDeclaredMadeForKids=video_is_for_kids
        )
    )

    # Call the API's videos.insert method to create and upload the video.
    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        #onBehalfOfContentOwner="Xq_vUZ8hXmQwZJVX3-cEvg",
        #onBehalfOfContentOwnerChannel="UCXq_vUZ8hXmQwZJVX3-cEvg",
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting "chunksize" equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (If the upload fails,
        # it will still be retried where it left off.) This is usually a best
        # practice, but if you're using Python older than 2.6 or if you're
        # running on App Engine, you should set the chunksize to something like
        # 1024 * 1024 (1 megabyte).
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
    )

    youtube_id = resumable_upload(insert_request)
    return(youtube_id)

# This method implements an exponential backoff strategy to resume a
# failed upload.
def resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            #print("Uploading file...")
            status, response = insert_request.next_chunk()
            if 'id' in response:
                printout("Video id '%s' was successfully uploaded." % response['id'])
            else:
                printout("The upload failed with an unexpected response: %s" % response)
                return None
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = "A retriable HTTP error %d occurred:\n%s" % (e.resp.status,
                                                                    e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = "A retriable error occurred: %s" % e

    if error is not None:
        printout(error)
        retry += 1
        if retry > MAX_RETRIES:
            printout("No longer attempting to retry.")
            return None

        max_sleep = 2 ** retry
        sleep_seconds = random.random() * max_sleep
        printout("Sleeping %f seconds and then retrying..." % sleep_seconds)
        time.sleep(sleep_seconds)
    return(response['id'])

######


### Define function ###

def lock_program(enable:bool=True):
    if enable:
        file = open(ENV_LOCKED_FILE, 'w')
        file.close()
    else:
        if os.path.exists(ENV_LOCKED_FILE):
            os.remove(ENV_LOCKED_FILE)

def is_program_locked():
    return True if os.path.exists(ENV_LOCKED_FILE) else False

def read_text(template_path:str) -> str:
    contents = ""   
    with open(template_path) as ftemplate:
        contents = ftemplate.read()

    return contents

def perform(process):
    if process is False:
        printout("FAILED TO PERFORM!")
        lock_program(False)
        exit()

def printout(text):
    print (f">> {text}\n")

def write_metadata(dst_path:str, metadata:list, headers:list):
    with open(dst_path, 'w', newline='') as fmetadata:
        writer = csv.DictWriter(fmetadata, fieldnames=headers, delimiter=';')

        writer.writeheader()
        
        for meta in metadata:
            writer.writerow(meta)

def read_metadata(src_path:str, headers:list):
    data = []
    with open(src_path, 'r') as fmetadata:
        metadata = csv.DictReader(fmetadata, fieldnames=headers, delimiter=';')
        next(metadata, None)
        for meta in metadata:
            data.append(meta)
    return data

def watermark_video(video_name:str, img_path:str) -> int:
    if not os.path.exists(img_path):
        printout("Watermark image not found! Skip watermarking video...")
        return True
    else:
        printout("Watermark image found! Begin watermarking video...")

    list_video = read_metadata(METADATA_GENERATED_PATH_FORMAT.format(OUTPUT_NAME=video_name), METADATA_HEADER)

    for video in list_video:
        if video['watermarked'] != METADATA_WATERMARKED:
            source = os.path.join(video['file_dir'], video['filename'])
            basename, ext = os.path.splitext(video['filename'])
            output = os.path.join(video['file_dir'], f"{basename} - watermarked{ext}")
            
            cmd = [
                FFMPEG_BIN_PATH,
                "-y", 
                "-hwaccel", "cuda",
                "-hwaccel_output_format", "cuda",
                "-i", source,
                "-i", img_path,
                "-filter_complex",
                (
                    f"[1:v]format=rgba,colorchannelmixer=aa=0.1[logo];" +
                    f"[0:v]scale_cuda=w=0:h=0:format=yuv420p:interp_algo=lanczos,hwdownload[video];" +
                    f"[video][logo]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2,fps=fps=60,format=yuv420p"
                ),
                "-c:v", "h264_nvenc",
                "-c:a", "copy",
                output
            ]

            result = subprocess.run(cmd)

            if result.returncode == 0:
                shutil.move(output, source)
                video['watermarked'] = METADATA_WATERMARKED
                write_metadata(METADATA_GENERATED_PATH_FORMAT.format(OUTPUT_NAME=video_name), list_video, METADATA_HEADER)
            else:
                return False

    print("\n")

    return True

def split_15min_video(src_path:str, dst_dir:str, dst_name:str, dst_ext:str) -> int:
    dst_path = os.path.join(dst_dir, f"{dst_name} %d{dst_ext}")
    os.makedirs(dst_dir, exist_ok=True)

    cmd = [
        FFMPEG_BIN_PATH, 
        "-i", src_path,
        "-f", "segment",
        "-map", "0",
        "-segment_time", "00:15:00",
        "-reset_timestamps", "1",
        "-c:v", "copy",
        "-c:a", "copy",
        dst_path
    ]

    result = subprocess.run(cmd)

    print("\n")

    return result.returncode

def write_metadata_video(dst_dir:str, dst_name:str, dst_ext:str, dst_title:str, additional_description:str="", additional_keywords:str="", base_description_file:str=ENV_TEMPLATE_DESCRIPTION_FILE, base_keywords_file:str=ENV_TEMPLATE_KEYWORDS_FILE) -> int:
    video_pattern = os.path.join(dst_dir, f"*{dst_ext}")
    list_video = glob.glob(rf"{video_pattern}")
    total_video = len(list_video)
    
    base_description = read_text(base_description_file)
    base_keywords = read_text(base_keywords_file)

    list_video_dict = []

    counter:int = 1
    for video in list_video:
        name = f"{dst_name} {counter} {total_video}{dst_ext}" if total_video > 1 else f"{dst_name}{dst_ext}"
        title =  f"{dst_title} (Part {counter} / {total_video})" if total_video > 1 else f"{dst_title}"
        description = f"{additional_description}\n\n{base_description}"
        keywords = f"{additional_keywords},{base_keywords}"

        list_video_dict.append({ 'id': counter, 'file_dir': dst_dir, 'filename': name, 'title': title, 'description': description, 'keywords': keywords, 'privacy_status': METADATA_PRIVACY_STATUS })
        shutil.move(video, os.path.join(dst_dir, name))
        counter += 1

    write_metadata(METADATA_GENERATED_PATH_FORMAT.format(OUTPUT_NAME=dst_name), list_video_dict, METADATA_HEADER)

    return 0

def process_video(dst_name):
    description_part = ""

    youtube_auth = get_youtube_instance(ENV_CLIENT_SECRETS_FILE, YOUTUBE_UPLOAD_SCOPE, YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION)
    if youtube_auth:
        printout("Successfully to authenticate youtube instance [v]")
        try:
            list_video_dict = read_metadata(METADATA_GENERATED_PATH_FORMAT.format(OUTPUT_NAME=dst_name), METADATA_HEADER)
            for video_dict in list_video_dict:
                if video_dict['youtube_id'] == "":
                    printout(f"Uploading video \"{video_dict['title']}\"")
                    upload_ok = upload_video(youtube_auth, video_dict)
                    write_metadata(METADATA_GENERATED_PATH_FORMAT.format(OUTPUT_NAME=dst_name), list_video_dict, METADATA_HEADER)
                    if upload_ok:
                        description_part += f"{video_dict['title']}: https://youtu.be/{video_dict['youtube_id']}\n"
                    else:
                        return False
            
            description_part += "\n" + video_dict['description']

            for video_dict in list_video_dict:
                printout(f"Rewriting description \"{video_dict['title']}\"")
                rewrite_description(youtube_auth, video_dict, description_part)
        except HttpError as e:
            printout("An HTTP error %d occurred:\n%s [x]" % (e.resp.status, e.content))
            return False
    else:
        printout("Failed to authenticate youtube instance [x]")
        return False

def rewrite_description(youtube, video_obj, video_description):
    video_id = video_obj['youtube_id']
    video_title = video_obj['title']
    video_category = 20

    body=dict(
        id=video_id,
        snippet=dict(
            title=video_title,
            categoryId=video_category,
            description=video_description,
        )
    )

    update_request = youtube.videos().update(
        part=",".join(body.keys()),
        body=body
    )

    result = update_request.execute()
    return result

def get_youtube_instance(secrets_file, upload_scope, api_service_name, api_version, prompt_code="Enter code: "):
    credentials = None
    oauth_file = os.path.join(BASE_PATH, f"{sys.argv[0]}-oauth2.json")

    if os.path.exists(oauth_file):
        credentials = Credentials.from_authorized_user_file(oauth_file, upload_scope)
    
    if credentials is None or not credentials.valid:
        flow = Flow.from_client_secrets_file(secrets_file, upload_scope)
        flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        auth_url, _ = flow.authorization_url()
        printout(f"Please open: {auth_url}")
        code = input(prompt_code)
        flow.fetch_token(code=code)
        credentials = flow.credentials

        with open(oauth_file, 'w') as foauth:
            foauth.write(credentials.to_json())

    return None if credentials is None or not credentials.valid else build(api_service_name, api_version, credentials=credentials)

def upload_video(youtube, video_obj):
    video_is_for_kids = False
    video_category = 22

    video_file = os.path.join(video_obj['file_dir'], video_obj['filename'])
    if not os.path.exists(video_file):
        printout("Please specify a valid file.")
        return False

    printout("Uploading...")
    youtube_id = initialize_upload(youtube, video_file, video_obj['title'], video_category, video_obj['description'], video_obj['keywords'], video_obj['privacy_status'], video_is_for_kids)
    
    if youtube_id is not None:
        output_video_list(video_obj['title'], youtube_id)
        video_obj['youtube_id'] = youtube_id
        printout("Uploaded [v]")
        return True
    else:
        printout("Failed to upload [x]")
        return False

### NEW FUNCTION ###

def rewrite_description2(youtube, video_obj, video_description):
    youtube = get_youtube_instance(ENV_CLIENT_SECRETS_FILE, YOUTUBE_UPLOAD_SCOPE, YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION)
    return rewrite_description(youtube, video_obj, video_description)

def process_video2(dst_name):
    description_part = ""

    youtube_auth = get_youtube_instance2(ENV_LOGIN_COOKIES_FILE, YOUTUBE_UPLOAD_SCOPE, YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION)
    if youtube_auth:
        printout("Successfully to authenticate youtube instance [v]")
        try:
            list_video_dict = read_metadata(METADATA_GENERATED_PATH_FORMAT.format(OUTPUT_NAME=dst_name), METADATA_HEADER)
            for video_dict in list_video_dict:
                if video_dict['youtube_id'] == "":
                    printout(f"Uploading video \"{video_dict['title']}\"")
                    upload_not_ok = not upload_video2(youtube_auth, video_dict)
                    write_metadata(METADATA_GENERATED_PATH_FORMAT.format(OUTPUT_NAME=dst_name), list_video_dict, METADATA_HEADER)
                    if upload_not_ok:
                        youtube_auth.close()
                        return False
                        
                description_part += f"{video_dict['title']}: https://youtu.be/{video_dict['youtube_id']}\n"
            
            description_part += "\n" + video_dict['description']

            for video_dict in list_video_dict:
                printout(f"Rewriting description \"{video_dict['title']}\"")
                rewrite_description2(youtube_auth, video_dict, description_part)

            youtube_auth.close()
            return True
        except HttpError as e:
            printout("An HTTP error %d occurred:\n%s [x]" % (e.resp.status, e.content))
            youtube_auth.close()
            return False
    else:
        printout("Failed to authenticate youtube instance [x]")
        return False

def get_youtube_instance2(secrets_file, upload_scope, api_service_name, api_version, prompt_code="Enter code: "):
    opts = None
    exe_path = ENV_CHROMEDRIVER_FILE

    f = open(secrets_file, 'r')
    data = f.read()
    f.close()

    if data.strip() == "":
        printout(f"Login cookies file at '{ENV_LOGIN_COOKIES_FILE}' is empty! Please copy your login cookies into that file (using 'EditThisCookie' plugin).")
        return None

    # opts = ChromeOptions()
    # opts.add_argument("--headless=new")
    driver = webdriver.Chrome(executable_path=exe_path, options=opts) if opts is not None else webdriver.Chrome(executable_path=exe_path)
    driver.get("https://youtube.com")

    data = json.loads(data)
    for cookie in data:
        cookie.pop('sameSite')
        driver.add_cookie(cookie)

    driver.get("https://studio.youtube.com")

    return driver

def upload_video2(youtube2, video_obj):
    video_is_for_kids = False
    video_category = 22
    youtube_id = None

    if video_category == 22:
        video_category = "CREATOR_VIDEO_CATEGORY_GADGETS"
    else:
        video_category = ""
    video_privacy_status = video_obj['privacy_status'].upper()

    video_file = os.path.join(video_obj['file_dir'], video_obj['filename'])
    if not os.path.exists(video_file):
        printout("Please specify a valid file.")
        return False

    printout("Uploading...")

    prepare_time = 6
    sleep_time = 3
    max_retries = 1800 / sleep_time
    count_retries = 0
    has_attribute = lambda attr : True if attr is not None else False

    time.sleep(prepare_time)

    # Click "Create" button (on top-right corner).
    printout('Click "Create" button (on top-right corner).')
    youtube2.find_elements(By.XPATH, "//ytcp-button[@id='create-icon']")[0].click_pro()

    # Click "Upload video" dropdown item.
    printout('Click "Upload video" dropdown item.')
    youtube2.find_elements(By.XPATH, "//tp-yt-paper-item[@id='text-item-0']")[0].click_pro()

    # Input file path to input file field (on changed, this will trigger submit file automatically).
    printout('Input file path to input file field (on changed, this will trigger submit file automatically).')
    youtube2.find_elements(By.XPATH, "//*[@id='content']/input[@name='Filedata']")[0].send_keys(video_file)

    time.sleep(prepare_time)

    printout("Begin uploading video...")
    # No error handling, need more research.
    xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[2]/div/div[1]/ytcp-video-upload-progress/tp-yt-iron-icon[@id='processing-badge']"
    processing_badge_el = youtube2.find_elements(By.XPATH, xpath)[0]
    xpath = "/html/body/ytcp-uploads-dialog"
    uploads_dialog_el = youtube2.find_elements(By.XPATH, xpath)[0]
    while True:
        # Check if error occurred.
        if has_attribute(uploads_dialog_el.get_attribute('has-error')):
            xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[2]/div/div[1]/ytcp-ve/div[1]"
            err_short_msg = youtube2.find_elements(By.XPATH, xpath)[0].text
            printout(f"Error occurred! Message => \"{err_short_msg}\"")
            return False

        # If processing badge become blue, (hopefully) it means video uploaded and begin processing video.
        if processing_badge_el.value_of_css_property('fill') == "rgb(62, 166, 255)":
            # Get youtube video id.
            printout("Done. Get youtube video id.")
            youtube_id = youtube2.find_elements(By.XPATH, "//*[@id='details']/ytcp-video-metadata-editor-sidepanel/ytcp-video-info/div/div[2]/div[1]/div[2]/span/a")[0].get_attribute('href')
            break
        
        time.sleep(sleep_time)
        count_retries += 1
        if count_retries >= max_retries:
            break


    # Click title div text field.
    printout("Click title div text field.")
    xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[1]/ytcp-social-suggestions-textbox/ytcp-form-input-container/div[1]/div[2]/div/ytcp-social-suggestion-input/div"
    #xpath = "//ytcp-social-suggestions-textbox[@id='title-textarea']/*[@id='container']/*[@id='outer']/*[@id='child-input']/*[@id='container-content']/*[@id='input']/*[@id='textbox']"
    youtube2.find_elements(By.XPATH, xpath)[0].click_pro()
    
    # Type video title.
    printout("Type video title.")
    youtube2.switch_to.active_element.send_keys(Keys.CONTROL, 'a')
    youtube2.switch_to.active_element.send_keys(video_obj['title'])

    # Click description div text field.
    printout("Click description div text field.")
    xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[2]/ytcp-social-suggestions-textbox/ytcp-form-input-container/div[1]/div[2]/div/ytcp-social-suggestion-input/div"
    #xpath = "//ytcp-social-suggestions-textbox[@id='description-textarea']/*[@id='container']/*[@id='outer']/*[@id='child-input']/*[@id='container-content']/*[@id='input']/*[@id='textbox']"
    youtube2.find_elements(By.XPATH, xpath)[0].click_pro()
    
    # Type video description.
    printout("Type video description.")
    youtube2.switch_to.active_element.send_keys(video_obj['description'])

    # Choose Made-For-Kids option by click radio button.
    printout("Choose Made-For-Kids option by click radio button.")
    if video_is_for_kids:
        xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[5]/ytkc-made-for-kids-select/div[4]/tp-yt-paper-radio-group/tp-yt-paper-radio-button[1]"
    else:
        xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[5]/ytkc-made-for-kids-select/div[4]/tp-yt-paper-radio-group/tp-yt-paper-radio-button[2]"
    youtube2.find_elements(By.XPATH, xpath)[0].click_pro()

    # Click advance detail.
    printout("Click advance detail.")
    xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/div/ytcp-button"
    youtube2.find_elements(By.XPATH, xpath)[0].click_pro()

    time.sleep(prepare_time)

    # Input keywords to input text field.
    printout("Input keywords to input text field.")
    xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-advanced/div[4]/ytcp-form-input-container/div[1]/div/ytcp-free-text-chip-bar/ytcp-chip-bar/div/input"
    youtube2.find_elements(By.XPATH, xpath)[0].send_keys(video_obj['keywords'])

    # Select video category.
    printout("Select video category.")
    xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-advanced/div[9]/div[3]/ytcp-form-select/ytcp-select"
    youtube2.find_elements(By.XPATH, xpath)[0].click_pro()
    xpath = f"/html/body/ytcp-text-menu/tp-yt-paper-dialog/tp-yt-paper-listbox/tp-yt-paper-item[@test-id='{video_category}']"
    youtube2.find_elements(By.XPATH, xpath)[0].click_pro()

    # Go to the last step.
    printout("Go to the last step.")
    xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/div[1]/ytcp-animatable/ytcp-stepper/div/div[4]/button"
    youtube2.find_elements(By.XPATH, xpath)[0].click_pro()

    time.sleep(prepare_time)

    # Select video privacy.
    printout("Select video privacy.")
    xpath = f"/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-uploads-review/div[2]/div[1]/ytcp-video-visibility-select/div[2]/tp-yt-paper-radio-group/tp-yt-paper-radio-button[@name='{video_privacy_status}']"
    youtube2.find_elements(By.XPATH, xpath)[0].click_pro()    

    # Submit video.
    printout("Submit video.")
    xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[2]/div/div[2]/ytcp-button[@id='done-button']"
    youtube2.find_elements(By.XPATH, xpath)[0].click_pro()

    time.sleep(prepare_time)
    
    # Close video process dialog.
    printout("Close video process dialog.")
    xpath = "/html/body/ytcp-uploads-still-processing-dialog/ytcp-dialog/tp-yt-paper-dialog/div[3]/ytcp-button"
    youtube2.find_elements(By.XPATH, xpath)[0].click_pro()
    
    if youtube_id is not None:
        output_video_list(video_obj['title'], youtube_id)
        youtube_id = youtube_id.split('/')[-1]
        video_obj['youtube_id'] = youtube_id
        printout("Uploaded [v]")
        return True
    else:
        printout("Either failed to upload or is timeout! Check your dashboard studio... [x]")
        return False

################

def prepare_environment(ffmpeg_path=None, use_data_api=False):
    if not os.path.exists(ENV_GEN_DIR):
        os.makedirs(ENV_GEN_DIR, exist_ok=True)
    if not os.path.exists(ENV_CONF_DIR):
        os.makedirs(ENV_CONF_DIR, exist_ok=True)
    if not os.path.exists(ENV_TEMPLATE_DESCRIPTION_FILE):
        f = open(ENV_TEMPLATE_DESCRIPTION_FILE, 'w')
        f.close()
    if not os.path.exists(ENV_TEMPLATE_KEYWORDS_FILE):
        f = open(ENV_TEMPLATE_KEYWORDS_FILE, 'w')
        f.close()

    if not os.path.exists(ENV_LOGIN_COOKIES_FILE):
        f = open(ENV_LOGIN_COOKIES_FILE, 'w')
        f.close()

    if not os.path.exists(ENV_DATA_FILE):
        f = open(ENV_DATA_FILE, 'w')
        w = csv.DictWriter(f, fieldnames=DATA_HEADER, delimiter=';')
        w.writeheader()
        f.close()

    global ENV_CLIENT_SECRETS_FILE
    global FFMPEG_BIN_PATH

    ENV_CLIENT_SECRETS_FILE = get_secret_id()

    if ffmpeg_path:
        FFMPEG_BIN_PATH = ffmpeg_path
    
    # Check if using youtube data API.
    if use_data_api:
        if ENV_CLIENT_SECRETS_FILE is None:
            printout("Can not find client secrets id!")
            return False
    else:
        if not os.path.exists(ENV_CHROMEDRIVER_FILE):
            printout("This program using Selenium with Chrome when not use Youtube Data API. Please download chromedriver from 'https://chromedriver.chromium.org/' and copy 'chromedriver.exe' into '.conf' directory.")
            return False
    
    return True

### Initialize program ###

def main(args):   
    # step 0
    printout("PERFORMING: Preparing environment...")
    perform(prepare_environment(args.ffmpeg_path, args.use_data_api))
    
    if is_program_locked():
        exit("Program already opening!")

    lock_program()

    if args.prepare_only:
        lock_program(False)
        exit()

    # step 1
    data = read_metadata(ENV_DATA_FILE, DATA_HEADER)

    for item in data:
        if item['status'] != DATA_STATUS_DONE:
            printout(f"PROCESSING VIDEO \"{item['source']}\"...")
            _, output_ext = os.path.splitext(item['source'])
            output_path = os.path.join(ENV_GEN_DIR, item['name'])

            if item['status'] == "":
                # step 2
                printout("PERFORMING: Splitting video to 15 minute long...")
                perform(split_15min_video(item['source'], output_path, item['name'], output_ext))
                item['status'] = DATA_STATUS_WRITE
                write_metadata(ENV_DATA_FILE, data, DATA_HEADER)

            if item['status'] == DATA_STATUS_WRITE:
                # step 3
                printout("PERFORMING: Writing metadata for splitted video...")
                perform(write_metadata_video(output_path, item['name'], output_ext, item['title'], item['description'], item['keywords']))
                item['status'] = DATA_STATUS_WATERMARK
                write_metadata(ENV_DATA_FILE, data, DATA_HEADER)

            if item['status'] == DATA_STATUS_WATERMARK:
                # step 2.5
                printout("PERFORMING: Watermarking splitted video...")
                perform(watermark_video(item['name'], ENV_WATERMARK_IMAGE_FILE))
                item['status'] = DATA_STATUS_UPLOAD
                write_metadata(ENV_DATA_FILE, data, DATA_HEADER)

            if item['status'] == DATA_STATUS_UPLOAD:
                # step 4
                printout("PERFORMING: Uploading splitted video...")
                perform(process_video2(item['name'])) if not args.use_data_api else perform(process_video(item['name']))
                item['status'] = DATA_STATUS_DONE
                write_metadata(ENV_DATA_FILE, data, DATA_HEADER)
    
    lock_program(False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Youtube-Uploader-Pipeline',
        description='Generate and upload compatible youtube video size.',
        epilog='Quotes of the day => Help yourself! Don\'t depends on the others.\n'
    )

    parser.add_argument('-f', '--ffmpeg-path')
    parser.add_argument('-a', '--use-data-api', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('-p', '--prepare-only', action=argparse.BooleanOptionalAction, default=False)

    main(parser.parse_args())
