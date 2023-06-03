import os
import argparse
import glob
import shutil

from googleapiclient.errors import HttpError

from yt15m.video import ffmpegapi
from yt15m.video import youtubeapi
from yt15m.data import metadata
from yt15m.data import template
from yt15m import helper

### Define variable ###

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

DATA_STATUS_WATERMARK = "Failed to watermarking video"
DATA_STATUS_WRITE = "Failed to writing metadata"
DATA_STATUS_UPLOAD = "Failed to uploading video"
DATA_STATUS_DONE = "Done"
DATA_HEADER = ['source', 'name', 'title', 'description', 'keywords', 'playlist', 'status']

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
METADATA_HEADER = ['id', 'file_dir', 'filename', 'title', 'description', 'keywords', 'privacy_status', 'watermark', 'playlist_id', 'youtube_id', 'status']
METADATA_PRIVACY_STATUS = "public"
METADATA_WATERMARKED = "Watermarked TM"
METADATA_STATUS_PLAYLIST = "Failed to adding part to playlist"
METADATA_STATUS_DESCRIPTION = "Failed to rewriting part description"
METADATA_STATUS_DONE = "Done"

FFMPEG_BIN_PATH = "ffmpeg"

# Initialize it first before use.
ENV_CLIENT_SECRETS_FILE = None

YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

VALID_PRIVACY_STATUSES = ("public", "private", "unlisted")

def get_secret_id():
    for file in os.listdir(ENV_CONF_DIR):
        if file.endswith(".json") and file.startswith("client_secret_"):
            selected_id = os.path.join(ENV_CONF_DIR, file)
            helper.log(f"CLIENT_SECRETS_ID : {selected_id}")
            return selected_id

    for file in os.listdir(BASE_PATH):
        if file.endswith(".json") and file.startswith("client_secret_"):
            src = os.path.join(BASE_PATH, file)
            dst = os.path.join(ENV_CONF_DIR, file)
            shutil.move(src, dst)
            helper.log(f"CLIENT_SECRETS_ID : {dst}")
            return dst

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

def perform(process):
    if process is False:
        helper.log("FAILED TO PERFORM!", False)
        lock_program(False)
        raise Exception("Failed to performed latest process!")

def watermark_video(video_name:str, img_path:str) -> int:
    if not os.path.exists(img_path):
        helper.log("Watermark image not found! Skip watermarking video...", False)
        return True
    else:
        helper.log("Watermark image found! Begin watermarking video...", True)

    list_video = metadata.read(METADATA_GENERATED_PATH_FORMAT.format(OUTPUT_NAME=video_name), METADATA_HEADER)

    for video in list_video:
        if video['watermarked'] != METADATA_WATERMARKED:
            source = os.path.join(video['file_dir'], video['filename'])
            
            watermark_ok = ffmpegapi.add_video_wm(source, source, img_path)

            if watermark_ok:
                video['watermarked'] = METADATA_WATERMARKED
                metadata.write(METADATA_GENERATED_PATH_FORMAT.format(OUTPUT_NAME=video_name), list_video, METADATA_HEADER)                
            else:
                return False

    return True

def split_15min_video(src_path:str, dst_dir:str, dst_name:str, dst_ext:str) -> int:
    dst_path = os.path.join(dst_dir, f"{dst_name}{dst_ext}")

    split_ok = ffmpegapi.split_video_eq(src_path, dst_path, "00:15:00")

    if split_ok:
        return True
    else:
        return False

def write_metadata_video(dst_dir:str, dst_name:str, dst_ext:str, dst_title:str, additional_description:str="", additional_keywords:str="", base_description_file:str=ENV_TEMPLATE_DESCRIPTION_FILE, base_keywords_file:str=ENV_TEMPLATE_KEYWORDS_FILE) -> int:
    video_pattern = os.path.join(dst_dir, f"*{dst_ext}")
    list_video = glob.glob(rf"{video_pattern}")
    total_video = len(list_video)
    
    base_description = template.read(base_description_file)
    base_keywords = template.read(base_keywords_file)

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

    return metadata.write(METADATA_GENERATED_PATH_FORMAT.format(OUTPUT_NAME=dst_name), list_video_dict, METADATA_HEADER)

def process_video(dst_name, playlist_id="", use_data_api=False, show_selenium_screen=False):
    description_part = ""
    video_category = 22

    up_strategy = None
    login_file = None

    if use_data_api:
        login_file = ENV_CLIENT_SECRETS_FILE
        up_strategy = youtubeapi.UPLOAD_STRATEGY_DATAAPI
    else:
        login_file = ENV_LOGIN_COOKIES_FILE
        up_strategy = youtubeapi.UPLOAD_STRATEGY_SELENIUM

    youtube_auth = youtubeapi.init_youtube(login_file, up_strategy, extra_data=dict(
        upload_scope=YOUTUBE_UPLOAD_SCOPE, 
        api_service_name=YOUTUBE_API_SERVICE_NAME, 
        api_version=YOUTUBE_API_VERSION,
        show_web_browser=show_selenium_screen,
        chromedriver_file=ENV_CHROMEDRIVER_FILE
        ))

    if youtube_auth:
        helper.log("Successfully to authenticate youtube instance.", True)
        try:
            source_path = METADATA_GENERATED_PATH_FORMAT.format(OUTPUT_NAME=dst_name)
            
            if metadata.is_not_update(source_path, METADATA_HEADER):
                list_video_dict = metadata.read(source_path, None)
                metadata.write(source_path, list_video_dict, METADATA_HEADER)
            
            list_video_dict = metadata.read(source_path, METADATA_HEADER)

            for video_dict in list_video_dict:
                if video_dict['status'] == "":
                    if video_dict['youtube_id'] == "":
                        helper.log(f"Uploading video \"{video_dict['title']}\"")
                        video_id = youtubeapi.upload_video(youtube_auth, os.path.join(video_dict['file_dir'], video_dict['filename']),
                                    video_dict['title'],
                                    video_category,
                                    video_dict['description'],
                                    video_dict['keywords'])
                        if video_id:
                            video_dict['youtube_id'] = video_id
                            metadata.write(source_path, list_video_dict, METADATA_HEADER)
                        else:
                            return False

                    video_dict['status'] = METADATA_STATUS_DESCRIPTION

                    metadata.write(source_path, list_video_dict, METADATA_HEADER)                

                description_part += f"{video_dict['title']}: https://youtu.be/{video_dict['youtube_id']}\n"
            description_part += "\n" + video_dict['description']

            for video_dict in list_video_dict:
                if video_dict['status'] == METADATA_STATUS_DESCRIPTION:
                    helper.log(f"Rewriting description \"{video_dict['title']}\"")
                    success = youtubeapi.rewrite_description(youtube_auth, video_dict['youtube_id'], description_part, extra_data=dict(
                        video_title=video_dict['title'],
                        video_category=video_category
                    ))

                    if not success:
                        return False
                    else:
                        if playlist_id != "":
                            video_dict['status'] = METADATA_STATUS_PLAYLIST
                        else:
                            video_dict['status'] = METADATA_STATUS_DONE

                    metadata.write(source_path, list_video_dict, METADATA_HEADER)

                if video_dict['status'] == METADATA_STATUS_PLAYLIST:
                    if video_dict['playlist_id'] == "":
                        helper.log(f"Adding \"{video_dict['title']}\" to playlist")
                        success = youtubeapi.add_playlist_item(youtube_auth, playlist_id, video_dict['youtube_id'])

                        if not success:
                            return False
                        else:
                            video_dict['playlist_id'] = playlist_id

                    video_dict['status'] = METADATA_STATUS_DONE
                    metadata.write(source_path, list_video_dict, METADATA_HEADER)

        except HttpError as e:
            helper.log("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content), False)
            return False
    else:
        helper.log("Failed to authenticate youtube instance", False)
        return False

    return True

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
        metadata.write(ENV_DATA_FILE, [], DATA_HEADER)
    else:
        if metadata.is_not_update(ENV_DATA_FILE, DATA_HEADER):
            md = metadata.read(ENV_DATA_FILE, None)
            metadata.write(ENV_DATA_FILE, md, DATA_HEADER)

    global ENV_CLIENT_SECRETS_FILE
    global FFMPEG_BIN_PATH

    ENV_CLIENT_SECRETS_FILE = get_secret_id()

    if ffmpeg_path:
        FFMPEG_BIN_PATH = ffmpeg_path
    
    # Check if using youtube data API.
    if use_data_api:
        if ENV_CLIENT_SECRETS_FILE is None:
            helper.log("Can not find client secrets id!", False)
            return False
    else:
        if not os.path.exists(ENV_CHROMEDRIVER_FILE):
            helper.log("This program using Selenium with Chrome when not using Youtube Data API. Please download chromedriver from 'https://chromedriver.chromium.org/' and copy 'chromedriver.exe' into '.conf' directory.", False)
            return False
    
    return True

### Initialize program ###

def start(video_source, video_name, video_title, video_description, video_keywords, video_playlist=None, pipeline_status=None, pipeline_options=None):
    use_data_api = False
    show_selenium_screen = False
    ffmpeg_path = 'ffmpeg'

    if pipeline_options:
        if pipeline_options['use_data_api']: 
            use_data_api = pipeline_options['use_data_api']
        if pipeline_options['show_selenium_screen']:
            show_selenium_screen = pipeline_options['show_selenium_screen']
        if pipeline_options['ffmpeg_path']:
            ffmpeg_path = pipeline_options['ffmpeg_path']

    try:
        # step 0
        helper.log("PERFORMING: Preparing environment...")
        perform(prepare_environment(ffmpeg_path, use_data_api))

        if pipeline_status != DATA_STATUS_DONE:
            helper.log(f"PROCESSING VIDEO \"{video_source}\"...")
            _, output_ext = os.path.splitext(video_source)
            output_path = os.path.join(ENV_GEN_DIR, video_name)

            if pipeline_status == "":
                # step 2
                helper.log("PERFORMING: Splitting video to 15 minute long...")
                perform(split_15min_video(video_source, output_path, video_name, output_ext))
                pipeline_status = DATA_STATUS_WRITE

            if pipeline_status == DATA_STATUS_WRITE:
                # step 3
                helper.log("PERFORMING: Writing metadata for splitted video...")
                perform(write_metadata_video(output_path, video_name, output_ext, video_title, video_description, video_keywords))
                pipeline_status = DATA_STATUS_WATERMARK

            if pipeline_status == DATA_STATUS_WATERMARK:
                # step 2.5
                helper.log("PERFORMING: Watermarking splitted video...")
                perform(watermark_video(video_name, ENV_WATERMARK_IMAGE_FILE))
                pipeline_status = DATA_STATUS_UPLOAD

            if pipeline_status == DATA_STATUS_UPLOAD:
                # step 4
                helper.log("PERFORMING: Uploading splitted video...")
                perform(process_video(video_name, playlist_id=video_playlist, use_data_api=use_data_api, show_selenium_screen=show_selenium_screen))
                pipeline_status = DATA_STATUS_DONE
    except:
        pass

    return pipeline_status


def main(args):   
    # step 0
    helper.log("PERFORMING: Preparing environment...")
    perform(prepare_environment(args.ffmpeg_path, args.use_data_api))
    
    if is_program_locked():
        exit("Program already opening!")

    lock_program()

    if args.prepare_only:
        lock_program(False)
        exit()

    # step 1
    data = metadata.read(ENV_DATA_FILE, DATA_HEADER)
    
    for item in data:
        if item['status'] != DATA_STATUS_DONE:
            helper.log(f"PROCESSING VIDEO \"{item['source']}\"...")
            _, output_ext = os.path.splitext(item['source'])
            output_path = os.path.join(ENV_GEN_DIR, item['name'])

            if item['status'] == "":
                # step 2
                helper.log("PERFORMING: Splitting video to 15 minute long...")
                perform(split_15min_video(item['source'], output_path, item['name'], output_ext))
                item['status'] = DATA_STATUS_WRITE
                metadata.write(ENV_DATA_FILE, data, DATA_HEADER)

            if item['status'] == DATA_STATUS_WRITE:
                # step 3
                helper.log("PERFORMING: Writing metadata for splitted video...")
                perform(write_metadata_video(output_path, item['name'], output_ext, item['title'], item['description'], item['keywords']))
                item['status'] = DATA_STATUS_WATERMARK
                metadata.write(ENV_DATA_FILE, data, DATA_HEADER)

            if item['status'] == DATA_STATUS_WATERMARK:
                # step 2.5
                helper.log("PERFORMING: Watermarking splitted video...")
                perform(watermark_video(item['name'], ENV_WATERMARK_IMAGE_FILE))
                item['status'] = DATA_STATUS_UPLOAD
                metadata.write(ENV_DATA_FILE, data, DATA_HEADER)

            if item['status'] == DATA_STATUS_UPLOAD:
                # step 4
                helper.log("PERFORMING: Uploading splitted video...")
                perform(process_video(item['name'], playlist_id=item['playlist'], use_data_api=args.use_data_api, show_selenium_screen=args.show_selenium_screen))
                item['status'] = DATA_STATUS_DONE
                metadata.write(ENV_DATA_FILE, data, DATA_HEADER)
    
    lock_program(False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Youtube-15Minutes-Pipeline',
        description='Generate and upload compatible youtube video size.'
    )

    parser.add_argument('--video-source')
    parser.add_argument('--video-name')
    parser.add_argument('--video-title')
    parser.add_argument('--video-description')
    parser.add_argument('--video-keywords')
    parser.add_argument('--video-playlist')
    
    parser.add_argument('--pipeline-last-status')

    parser.add_argument('-f', '--ffmpeg-path')
    parser.add_argument('-a', '--use-data-api', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('-p', '--prepare-only', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('-s', '--show-selenium-screen', action=argparse.BooleanOptionalAction, default=False)

    main(parser.parse_args())
