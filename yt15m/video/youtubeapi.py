import ytdata_api
import ytselenium_api

UPLOAD_STRATEGY_DATAAPI = 'upstr_dataapi'
UPLOAD_STRATEGY_SELENIUM = 'upstr_selenium'

def init_youtube(login_file, upload_strategy, extra_data=dict()):
    if upload_strategy == UPLOAD_STRATEGY_DATAAPI:
        return ytdata_api.init_youtube(login_file, **extra_data)
    elif upload_strategy == UPLOAD_STRATEGY_SELENIUM:
        return ytselenium_api.init_youtube(login_file, **extra_data)
    else:
        raise

def upload_video(youtube, upload_strategy, video_file, video_title, video_category, video_description, video_keywords, video_privacy_status='public', video_is_for_kids=False):
    if upload_strategy == UPLOAD_STRATEGY_DATAAPI:
        return ytdata_api.upload_video(youtube, video_file, video_title, video_category, video_description, video_keywords, video_privacy_status, video_is_for_kids)
    elif upload_strategy == UPLOAD_STRATEGY_SELENIUM:
        return ytselenium_api.upload_video(youtube, video_file, video_title, video_category, video_description, video_keywords, video_privacy_status, video_is_for_kids)
    else:
        raise

def rewrite_description(youtube, upload_strategy, video_id, video_description, extra_data=dict()):
    if upload_strategy == UPLOAD_STRATEGY_DATAAPI:
        return ytdata_api.rewrite_description(youtube, video_id, video_description, **extra_data)
    elif upload_strategy == UPLOAD_STRATEGY_SELENIUM:
        return ytselenium_api.rewrite_description(youtube, video_id, video_description)
    else:
        raise

def add_playlist_item(youtube, upload_strategy, playlist_id, video_id):
    if upload_strategy == UPLOAD_STRATEGY_DATAAPI:
        return ytdata_api.add_playlist_item(youtube, playlist_id, video_id)
    elif upload_strategy == UPLOAD_STRATEGY_SELENIUM:
        return ytselenium_api.add_playlist_item(youtube, playlist_id, video_id)
    else:
        raise