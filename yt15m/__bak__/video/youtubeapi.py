from yt15m.video import ytdata_api, ytselenium_api

UPLOAD_STRATEGY_DATAAPI = 'upstr_dataapi'
UPLOAD_STRATEGY_SELENIUM = 'upstr_selenium'

def init_youtube(login_file, upload_strategy, extra_data=dict()):
    instance = None
    if upload_strategy == UPLOAD_STRATEGY_DATAAPI:
        instance = ytdata_api.init_youtube(login_file, **extra_data)
    elif upload_strategy == UPLOAD_STRATEGY_SELENIUM:
        instance = ytselenium_api.init_youtube(login_file, **extra_data)
    else:
        raise

    return (instance, upload_strategy)

def upload_video(youtube, video_file, video_title, video_category, video_description, video_keywords, video_privacy_status='public', video_is_for_kids=False):
    youtube, upload_strategy = youtube
    if upload_strategy == UPLOAD_STRATEGY_DATAAPI:
        return ytdata_api.upload_video(youtube, video_file, video_title, video_category, video_description, video_keywords, video_privacy_status, video_is_for_kids)
    elif upload_strategy == UPLOAD_STRATEGY_SELENIUM:
        return ytselenium_api.upload_video(youtube, video_file, video_title, video_category, video_description, video_keywords, video_privacy_status, video_is_for_kids)
    else:
        raise

def rewrite_description(youtube, video_id, video_description, extra_data=dict()):
    youtube, upload_strategy = youtube
    if upload_strategy == UPLOAD_STRATEGY_DATAAPI:
        return ytdata_api.rewrite_description(youtube, video_id, video_description, **extra_data)
    elif upload_strategy == UPLOAD_STRATEGY_SELENIUM:
        return ytselenium_api.rewrite_description(youtube, video_id, video_description)
    else:
        raise

def add_playlist_item(youtube, playlist_id, video_id):
    youtube, upload_strategy = youtube
    if upload_strategy == UPLOAD_STRATEGY_DATAAPI:
        return ytdata_api.add_playlist_item(youtube, playlist_id, video_id)
    elif upload_strategy == UPLOAD_STRATEGY_SELENIUM:
        return ytselenium_api.add_playlist_item(youtube, playlist_id, video_id)
    else:
        raise