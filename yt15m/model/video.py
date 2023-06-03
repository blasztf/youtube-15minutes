

class VideoModel:
    
    def __init__(self, video_file, video_title, video_category, video_description, video_keywords, video_privacy_status, video_is_for_kids) -> None:
        self.file = video_file
        self.title = video_title
        self.category = video_category
        self.description = video_description
        self.keywords = video_keywords
        self.privacy_status = video_privacy_status
        self.is_for_kids = video_is_for_kids

class VideoModelBuilder:

    @staticmethod
    def prepare():
        return VideoModelBuilder()

    def __init__(self) -> None:
        self.privacy_status = 'public'
        self.for_kids = False

    def file(self, file):
        self.sfile = file
        return self

    def title(self, title):
        self.stitle = title
        return self

    def category(self, category):
        self.scategory = category
        return self

    def description(self, description):
        self.sdescription = description
        return self

    def keywords(self, keywords):
        self.skeywords = keywords
        return self
    
    def privacy_status(self, privacy_status):
        self.sprivacy_status = privacy_status
        return self

    def is_for_kids(self, is_for_kids):
        self.for_kids = is_for_kids
        return self

    def build(self):
        return VideoModel(self.sfile, self.stitle, self.scategory, self.sdescription, self.skeywords, self.sprivacy_status, self.for_kids)