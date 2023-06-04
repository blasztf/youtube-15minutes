from yt15m.model.video import VideoModel
from yt15m.iface.context import Context

class Uploader(Context):

    def __init__(self) -> None:
        super().__init__(None)

    # context alias
    @property
    def youtube(self):
        return self.context

    def auth(self) -> bool:
        self.__context = self.auth_to_youtube()
        return self.__context is not None

    def auth_to_youtube(self):
        pass

    def upload_video(self, video_model: VideoModel):
        pass

    def rewrite_description(self, video_id: str, video_model: VideoModel):
        pass

    def add_video_to_playlist(self, playlist_id: str, video_id: str):
        pass