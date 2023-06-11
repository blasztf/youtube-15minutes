import os
from yt15m.iface.repository import Repository
from yt15m.model.video import VideoModel, VideoModelBuilder
from yt15m.datastore.csv import CsvDatastore
from yt15m.util.helper import rtsg

class VideoRepository(Repository):

    def __init__(self, path, name) -> None:
        super().__init__(CsvDatastore(os.path.join(path, 'Video'), os.path.join(path, name)))

    def add(self, model: VideoModel):
        video_id = os.path.basename(model.file)
        if self.context.create(id=video_id, file=model.file, title=model.title, description=model.description, category=model.category, keywords=model.keywords, privacy_status=model.privacy_status, is_for_kids=model.is_for_kids, playlist=model.playlist, vid=model.vid, progress=model.progress):
            model.id = video_id
            return model
        else: 
            return None

    def all(self):
        all_data: list[dict[str, object]] = self.context.read_all(id=None, file=None, title=None, description=None, category=None, keywords=None, privacy_status=None, is_for_kids=None, playlist=None, vid=None, progress=None)
        all_model: list[VideoModel] = []
        
        vm_builder: VideoModelBuilder = VideoModelBuilder()
        for data in all_data:
          all_model.append(self.parse(vm_builder, data))

        return all_model

    def find(self, id):
        data: dict[str, object] = self.context.read(id, 'id', file=None, title=None, description=None, category=None, keywords=None, privacy_status=None, is_for_kids=None, playlist=None, vid=None, progress=None)
        vm_builder: VideoModelBuilder = VideoModelBuilder()
        return self.parse(vm_builder, data) if data is not None else None

    def update(self, model: VideoModel):
        return model if self.context.update(model.id, 'id', file=model.file, title=model.title, description=model.description, category=model.category, keywords=model.keywords, privacy_status=model.privacy_status, is_for_kids=model.is_for_kids, playlist=model.playlist, vid=model.vid, progress=model.progress) else None

    def remove(self, model: VideoModel):
        return model if self.context.delete(model.id, 'id', file=None, title=None, description=None, category=None, keywords=None, privacy_status=None, is_for_kids=None, playlist=None, vid=None, progress=None) else None

    def parse(self, vm_builder: VideoModelBuilder, data: dict[str, object]):
        vm_builder.id(data['id'])
        vm_builder.file(data['file'])
        vm_builder.title(data['title'])
        vm_builder.description(data['description'])
        vm_builder.category(data['category'])
        vm_builder.keywords(data['keywords'])
        vm_builder.privacy_status(data['privacy_status'])
        vm_builder.is_for_kids(data['is_for_kids'])
        vm_builder.playlist(data['playlist'])
        vm_builder.vid(data['vid'])
        vm_builder.progress(data['progress'])

        return vm_builder.build()