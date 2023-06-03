import os
import time
import random
import http.client
import httplib2

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from yt15m.iface.uploader import Uploader
from yt15m.model.video import VideoModel
from yt15m.util import helper

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

class YoutubeDataUploader(Uploader):

    def __init__(self) -> None:
        pass

    def prepare_auth(self, secrets_file, upload_scope, api_service_name, api_version, prompt_code="Please open {url}\nEnter code: "):
        self.__requirements = {
            'secrets_file': secrets_file,
            'upload_scope': upload_scope,
            'api_service_name': api_service_name,
            'api_version': api_version,
            'prompt_code': prompt_code
        }

    def auth_to_youtube(self):
        credentials = None
    
        pathname, ext = os.path.splitext(self.__requirements['secrets_file'])
        oauth_file = f"{pathname}-oauth{ext}"

        if os.path.exists(oauth_file):
            credentials = Credentials.from_authorized_user_file(oauth_file, self.__requirements['upload_scope'])
        
        if credentials is None or not credentials.valid:
            flow = Flow.from_client_secrets_file(self.__requirements['secrets_file'], self.__requirements['upload_scope'])
            flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
            auth_url, _ = flow.authorization_url()
            code = input(self.__requirements['prompt_code'].format(url=auth_url))
            flow.fetch_token(code=code)
            credentials = flow.credentials

            with open(oauth_file, 'w') as foauth:
                foauth.write(credentials.to_json())

        return None if credentials is None or not credentials.valid else build(self.__requirements['api_service_name'], self.__requirements['api_version'], credentials=credentials)

    def upload_video(self, video_model: VideoModel) -> str:
        tags = None
        if video_model.keywords:
            tags = video_model.keywords.split(",")

        body=dict(
            snippet=dict(
                title=video_model.title,
                description=video_model.description,
                tags=tags,
                categoryId=video_model.category
            ),
            status=dict(
                privacyStatus=video_model.privacy_status,
                selfDeclaredMadeForKids=video_model.is_for_kids
            )
        )

        insert_request = self.youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(video_model.file, chunksize=-1, resumable=True)
        )

        youtube_id = self.__resumable_upload(insert_request)
        return youtube_id

    def rewrite_description(self, video_id: str, video_model: VideoModel) -> str:
        body=dict(
            id=video_id,
            snippet=dict(
                title=video_model.title,
                categoryId=video_model.category,
                description=video_model.description,
            )
        )

        update_request = self.youtube.videos().update(
            part=",".join(body.keys()),
            body=body
        )

        result = update_request.execute()

        return result['id'] if result else None

    def add_video_to_playlist(self, playlist_id: str, video_id: str) -> str:
        body=dict(
            snippet=dict(
                playlistId=playlist_id,
                resourceId=dict(
                    kind="youtube#video",
                    videoId=video_id
                )
            )
        )

        insert_request = self.youtube.playlistItems().insert(
            part=",".join(body.keys()),
            body=body
        )

        result = insert_request.execute()

        return result['snippet']['resourceId']['videoId'] if result else None


    def __resumable_upload(insert_request):
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

        response = None
        error = None
        retry = 0
        while response is None:
            try:
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