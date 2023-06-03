from yt15m.model.video import VideoModel

class Uploader:

    @property
    def youtube(self):
        return self.__context

    @property
    def context(self):
        return self.__context

    def auth(self):
        self.__context = self.auth_to_youtube()

    def auth_to_youtube(self):
        pass

    def upload_video(self, video_model: VideoModel):
        pass

    def rewrite_description(self, video_id: str, video_model: VideoModel):
        pass

    def add_video_to_playlist(self, playlist_id: str, video_id: str):
        pass