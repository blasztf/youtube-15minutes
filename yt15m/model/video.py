

class VideoModel:
    
    def __init__(self, video_id, video_file, video_title, video_category, video_description, video_keywords, video_privacy_status, video_is_for_kids, video_playlist, video_vid, video_progress) -> None:
        self.id = video_id
        self.file = video_file
        self.title = video_title
        self.category = video_category
        self.description = video_description
        self.keywords = video_keywords
        self.privacy_status = video_privacy_status
        self.is_for_kids = video_is_for_kids
        self.playlist = video_playlist
        self.vid = video_vid
        self.progress = video_progress

class VideoModelBuilder:

    def __init__(self, video_model: VideoModel = None) -> None:
        if video_model is not None:
            self.id(video_model.id)
            self.file(video_model.file)
            self.title(video_model.title)
            self.category(video_model.category)
            self.description(video_model.description)
            self.keywords(video_model.keywords)
            self.privacy_status(video_model.privacy_status)
            self.is_for_kids(video_model.is_for_kids)
            self.playlist(video_model.playlist)
            self.vid(video_model.vid)
            self.progress(video_model.progress)
        else:
            self.id(None)
            self.privacy_status('public')
            self.is_for_kids(False)
            self.playlist(None)
            self.vid(None)
            self.progress(None)

    def id(self, id) -> 'VideoModelBuilder':
        self.sid = id
        return self

    def file(self, file) -> 'VideoModelBuilder':
        self.sfile = file
        return self

    def title(self, title) -> 'VideoModelBuilder':
        self.stitle = title
        return self

    def category(self, category) -> 'VideoModelBuilder':
        self.scategory = category
        return self

    def description(self, description) -> 'VideoModelBuilder':
        self.sdescription = description
        return self

    def keywords(self, keywords) -> 'VideoModelBuilder':
        self.skeywords = keywords
        return self
    
    def privacy_status(self, privacy_status) -> 'VideoModelBuilder':
        self.sprivacy_status = privacy_status
        return self

    def is_for_kids(self, is_for_kids) -> 'VideoModelBuilder':
        self.for_kids = is_for_kids
        return self

    def playlist(self, playlist) -> 'VideoModelBuilder':
        self.splaylist = playlist
        return self

    def vid(self, vid) -> 'VideoModelBuilder':
        self.svid = vid
        return self

    def progress(self, progress) -> 'VideoModelBuilder':
        self.sprogress = progress
        return self

    def build(self):
        return VideoModel(self.sid, self.sfile, self.stitle, self.scategory, self.sdescription, self.skeywords, self.sprivacy_status, self.for_kids, self.splaylist, self.svid, self.sprogress)