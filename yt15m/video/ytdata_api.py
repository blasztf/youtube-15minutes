import os
import sys
import time
import random
import http.client
import httplib2

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from yt15m import helper

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
  http.client.IncompleteRead, http.client.ImproperConnectionState,
  http.client.CannotSendRequest, http.client.CannotSendHeader,
  http.client.ResponseNotReady, http.client.BadStatusLine)

def init_youtube(secrets_file, upload_scope, api_service_name, api_version, prompt_code="Please open {url}\nEnter code: ", **kwargs):
    credentials = None
    
    pathname, ext = os.path.splitext(secrets_file)
    oauth_file = f"{pathname}-oauth{ext}"

    if os.path.exists(oauth_file):
        credentials = Credentials.from_authorized_user_file(oauth_file, upload_scope)
    
    if credentials is None or not credentials.valid:
        flow = Flow.from_client_secrets_file(secrets_file, upload_scope)
        flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
        auth_url, _ = flow.authorization_url()
        code = input(prompt_code.format(url=auth_url))
        flow.fetch_token(code=code)
        credentials = flow.credentials

        with open(oauth_file, 'w') as foauth:
            foauth.write(credentials.to_json())

    return None if credentials is None or not credentials.valid else build(api_service_name, api_version, credentials=credentials)

def upload_video(youtube, video_file, video_title, video_category, video_description, video_keywords, video_privacy_status='public', video_is_for_kids=False, **kwargs):
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

    insert_request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
    )

    youtube_id = __resumable_upload(insert_request)
    return youtube_id

def rewrite_description(youtube, video_id, video_description, video_title, video_category, **kwargs):
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

    return result['id'] if result else None

def add_playlist_item(youtube, playlist_id, video_id, **kwargs):
    body=dict(
        snippet=dict(
            playlistId=playlist_id,
            resourceId=dict(
                kind="youtube#video",
                videoId=video_id
            )
        )
    )

    insert_request = youtube.playlistItems().insert(
        part=",".join(body.keys()),
        body=body
    )

    result = insert_request.execute()

    return result['snippet']['resourceId']['videoId'] if result else None

def __resumable_upload(insert_request):
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            #print("Uploading file...")
            status, response = insert_request.next_chunk()
            if 'id' in response:
                helper.log("Video id '%s' was successfully uploaded." % response['id'], True)
            else:
                helper.log("The upload failed with an unexpected response: %s" % response, False)
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
        helper.log(error, False)
        retry += 1
        if retry > MAX_RETRIES:
            helper.log("No longer attempting to retry.", False)
            return None

        max_sleep = 2 ** retry
        sleep_seconds = random.random() * max_sleep
        helper.log("Sleeping %f seconds and then retrying..." % sleep_seconds, False)
        time.sleep(sleep_seconds)

    return(response['id'])
