from yt15m.model.video import VideoModelBuilder, VideoModel
from yt15m.editor.ffmpeg import FfmpegEditor
from yt15m.uploader.ytapi import YoutubeApiUploader
from yt15m.uploader.ytweb import YoutubeWebUploader
from yt15m.iface.editor import Editor
from yt15m.iface.uploader import Uploader
from yt15m.iface.repository import Repository
from yt15m.repository.video import VideoRepository

#############

import os
import argparse

from yt15m.util.helper import *

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

ENV_DIRE_CONF = os.path.join(BASE_PATH, ".conf")
ENV_FILE_LOCK = os.path.join(ENV_DIRE_CONF, ".lock")
ENV_FILE_DONE = ".done"

ENV_YTAPI_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube"]
ENV_YTAPI_API_SERVICE_NAME = "youtube"

ENV_EDITOR_CHOICES = ['ffmpeg']
ENV_UPLOADER_CHOICES = ['web', 'api']

PROGRESS_UPLOAD = "Error when uploading video"
PROGRESS_PLAYLIST = "Error when adding video to playlist"
PROGRESS_REWRITING = "Error when rewriting description part to video description"
PROGRESS_DONE = "Done"


def unlock_program():
    lock_program(False)
    
def lock_program(enable:bool=True):
    if enable:
        file = open(ENV_FILE_LOCK, 'w')
        file.close()
    else:
        if os.path.exists(ENV_FILE_LOCK):
            os.remove(ENV_FILE_LOCK)

def is_program_locked():
    return True if os.path.exists(ENV_FILE_LOCK) else False

def perform(process):
    if not process[0]:
        raise PerformError(process[1])

def prepare_environment(**kwargs):
    if not os.path.exists(ENV_DIRE_CONF):
        os.makedirs(ENV_DIRE_CONF, exist_ok=True)
    
    if kwargs['editor'] == 'ffmpeg':
        if kwargs['ffmpeg_path'] != 'ffmpeg' and not os.path.exists(kwargs['ffmpeg_path']):
            return (False, PerformResult('E999', "FFMPEG => FFMPEG binary not exists"))

    if kwargs['uploader'] == 'web':
        if kwargs['cookie_login_path'] is None or not os.path.exists(kwargs['cookie_login_path']):
            return (False, PerformResult('E999', "YTWEB => Login cookie file not exists"))
        if kwargs['chromedriver_path'] != 'chromedriver.exe' and not os.path.exists(kwargs['chromedriver_path']):
            return (False, PerformResult('E999', "YTWEB => Chromedriver binary not exists"))
    elif kwargs['uploader'] == 'api':
        if kwargs['secret_client_path'] is None or not os.path.exists(kwargs['secret_client_path']):
            return (False, PerformResult('E999', "YTAPI => Secret client json file not exists"))

    if kwargs['video_file'] is None or not os.path.exists(kwargs['video_file']):
        return (False, PerformResult('E999', "Video file not exists"))
    
    return (True, None)

def build_video_model(set_model, video_file=None, video_title=None, video_description=None, video_category=None, video_keywords=None, video_privacy=None, video_for_kids=None, video_playlist=None, video_vid=None, video_progress=None, **kwargs):   
    try:
        builder = VideoModelBuilder()
        builder.id(os.path.splitext(os.path.basename(video_file)))
        builder.file(rtsg(video_file))
        builder.title(rtsg(video_title))
        builder.description(rtsg(video_description))
        builder.category(rtsg(video_category))
        builder.keywords(rtsg(video_keywords))
        builder.privacy_status(rtsg(video_privacy))
        builder.is_for_kids(rtsg(video_for_kids))
        builder.playlist(rtsg(video_playlist))
        builder.vid(rtsg(video_vid))
        builder.progress(rtsg(video_progress))

        set_model(builder.build())

        return (True, None)
    except Exception:
        return (False, PerformResult('E001', "Error building video model"))

def choose_editor(set_editor, editor=None, ffmpeg_path=None, **kwargs):
    if editor == 'ffmpeg':
        set_editor(FfmpegEditor(ffmpeg_path=ffmpeg_path))
    else:
        return (False, PerformResult('E002', "Editor not supported"))

    return (True, None)

def choose_uploader(set_uploader, uploader=None, cookie_login_path=None, show_web_browser=None, chromedriver_path=None, secret_client_path=None, api_version=None, **kwargs):
    uinst = None
    if uploader == 'web':
        uinst = YoutubeWebUploader(auth_cookies_file=cookie_login_path, show_web_browser=show_web_browser, chromedriver_file=chromedriver_path)
    elif uploader == 'api':
        uinst = YoutubeApiUploader(secrets_file=secret_client_path, upload_scope=ENV_YTAPI_UPLOAD_SCOPE, api_service_name=ENV_YTAPI_API_SERVICE_NAME, api_version=api_version)
    else:
        return (False, PerformResult('E003', "Uploader not supported"))
    
    if uinst.auth():
        set_uploader(uinst)
    else:
        return (False, PerformResult('E003', "Uploader failed to authenticate"))

    return (True, None)

def split_video(set_list_video, dst_path: str, editor: Editor, video_model: VideoModel, **kwargs):
    if editor.split_equally(video_model.file, os.path.join(dst_path, os.path.basename(video_model.file))):
        set_list_video(os.listdir(dst_path))
    else:
        return (False, PerformResult('E004', "Error when splitting video"))
    
    return (True, None)

def build_fragments_model(set_fragments, dst_path: str, repo: Repository, video_model: VideoModel, list_fragment: list[str], **kwargs):
    builder = VideoModelBuilder(video_model)

    fragments = []
    fragments_size = len(list_fragment)
    for index in range(fragments_size):
        fname = list_fragment[index]
        video = builder.title(f"{video_model.title} (Part {index + 1} / {fragments_size})").file(os.path.join(dst_path, fname)).progress(PROGRESS_UPLOAD).build()
        if repo.add(video) is not None:
            fragments.append(video)
        else:
            return (False, PerformResult('E008', "Error when adding new video fragments to repo"))

    if fragments_size == 1:
        builder = VideoModelBuilder(fragments[0])
        video = builder.title(video_model.title).build()
        fragments[0] = video
        repo.update(video)

    set_fragments(fragments)
    
    return (True, None)

def retrieve_fragments_model(set_fragments, repo: Repository, **kwargs):
    set_fragments(repo.all())
    return (True, None)

def upload_video(set_description_part: str, repo: Repository, uploader: Uploader, fragments: list[VideoModel], **kwargs):
    description_part = ""
    fragments_size = len(fragments)
    for index in range(fragments_size):
        video = fragments[index]
        if video.progress == PROGRESS_UPLOAD:
            video.vid = uploader.upload_video(video)
            if video.vid is not None:
                video.progress = PROGRESS_REWRITING
                repo.update(video)

        if video.vid is None:
            return (False, PerformResult('E005', PROGRESS_UPLOAD))
        else:
            description_part += f"PART {index + 1} : https://youtu.be/{video.vid}\n"

    if fragments[0].playlist is not None:
        description_part += f"\nPLAYLIST : {fragments[0].playlist}\n"

    set_description_part(description_part)
    return (True, None)

def update_video(description_part: str, repo: Repository, uploader: Uploader, fragments: list[VideoModel], **kwargs):
    for video in fragments:
        if video.progress == PROGRESS_REWRITING:
            if uploader.rewrite_description(f"{description_part}\n\n{video.description}", video.vid, video):
                if video.playlist is not None:
                    video.progress = PROGRESS_PLAYLIST
                else:
                    video.progress = PROGRESS_DONE
                repo.update(video)
            else:
                return (False, PerformResult('E007', PROGRESS_REWRITING))

        if video.progress == PROGRESS_PLAYLIST:
            if uploader.add_video_to_playlist(video.playlist, video.vid):
                video.progress = PROGRESS_DONE
                repo.update(video)
            else:
                return (False, PerformResult('E006', PROGRESS_PLAYLIST))

    return (True, None)

def main(args):
    args = vars(args)
    
    if args['verbose']:
        enable_log()
    
    if is_program_locked():
        error_already_running = "Program already running! Try again later..."
        log(f"FATAL: {error_already_running}", False)
        err(vars(PerformResult('E000', error_already_running)))
        exit()

    lock_program()

    try:
        # step 0
        log("PERFORM: Preparing environment...")
        perform(prepare_environment(**args))

        # step 1
        log("PERFORM: Building video model...")
        video_model, set_video_model = use_hook()
        perform(build_video_model(set_video_model, **args))

        dst_path, _ = os.path.splitext(video_model[0].file)
        dst_path = dst_path + "_yt15m"

        if not os.path.exists(os.path.join(dst_path, ENV_FILE_DONE)):
            # step 2
            log("PERFORM: Choosing editor...")    
            editor, set_editor = use_hook()
            perform(choose_editor(set_editor, **args))

            # step 3
            log("PERFORM: Choosing uploader...")
            uploader, set_uploader = use_hook()
            perform(choose_uploader(set_uploader, **args))

            os.makedirs(dst_path, exist_ok=True)

            fragments, set_fragments = use_hook()
            recorder = VideoRepository(dst_path, 'fragments')

            if len(os.listdir(dst_path)) <= 1:
                # step 4
                log("PERFORM: Splitting video to 15-minutes long...")
                list_video, set_list_video = use_hook()
                perform(split_video(set_list_video, dst_path, *editor, *video_model))
                perform(build_fragments_model(set_fragments, dst_path, recorder, *video_model, *list_video))
            else:
                # step 4.1
                log("PERFORM: Splitted video found! Retrieving fragments model...")
                perform(retrieve_fragments_model(set_fragments, recorder))
            

            # step 5
            log("PERFORM: Uploading video fragment to youtube...")
            description_part, set_description_part = use_hook()
            perform(upload_video(set_description_part, recorder, *uploader, *fragments))

            # step 6
            log("PERFORM: Updating video fragment in youtube...")
            perform(update_video(*description_part, recorder, *uploader, *fragments))

        out(vars(PerformResult()))

    except PerformError as pe:
        log(f"FAILED TO PERFORM: {pe.message}", False)
        err(vars(pe.result))

    finally:
        unlock_program()

    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='python pipeline.py',
        description="Transform video to multiple 15-minutes long video (unverified youtube channel limitation) and upload it to youtube channel.",
        epilog="\n"
    )

    parser.add_argument('-v', '--verbose', action=argparse.BooleanOptionalAction, default=False)
    # parser.add_argument('-p', '--prepare-only', action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument('-e', '--editor', choices=ENV_EDITOR_CHOICES, default='ffmpeg')
    parser.add_argument('-u', '--uploader', choices=ENV_UPLOADER_CHOICES, default='web')

    ### Editor ###

    # group_editor = parser.add_argument_group('editor')

    group_editor_ffmpeg = parser.add_argument_group('editor > ffmpeg')
    group_editor_ffmpeg.add_argument('--ffmpeg-path', default='ffmpeg')

    ### Uploader ###

    # group_uploader = parser.add_argument_group('uploader')

    group_uploader_web = parser.add_argument_group('uploader > web')
    group_uploader_web.add_argument('--cookie-login-path')
    group_uploader_web.add_argument('--show-web-browser', action=argparse.BooleanOptionalAction, default=False)
    group_uploader_web.add_argument('--chromedriver-path', default='chromedriver.exe')

    group_uploader_api = parser.add_argument_group('uploader > api')
    group_uploader_api.add_argument('--secret-client-path')
    group_uploader_api.add_argument('--api-version', default='v3')

    ### Model ###

    # group_model = parser.add_argument_group('model')

    group_model_video = parser.add_argument_group('model > video')
    group_model_video.add_argument('--video-file')
    group_model_video.add_argument('--video-title')
    group_model_video.add_argument('--video-category')
    group_model_video.add_argument('--video-description')
    group_model_video.add_argument('--video-keywords')
    group_model_video.add_argument('--video-privacy')
    group_model_video.add_argument('--video-for-kids')
    group_model_video.add_argument('--video-playlist')
    group_model_video.add_argument('--video-vid')
    group_model_video.add_argument('--video-progress')
    
    main(parser.parse_args())