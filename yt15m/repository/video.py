from yt15m.iface.repository import Repository
from yt15m.model.video import VideoModel, VideoModelBuilder
from yt15m.datastore.csv import CsvDatastore

class VideoRepository(Repository):

    def __init__(self, name) -> None:
        super().__init__(CsvDatastore('Video', name))

    def add(self, model: VideoModel):
        return model if self.context.create(file=model.file, title=model.title, description=model.description, category=model.category, keywords=model.keywords, privacy_status=model.privacy_status, is_for_kids=model.is_for_kids) else None

    def all(self):
        all_data: list[dict[str, object]] = self.context.read_all(file=None, title=None, description=None, category=None, keywords=None, privacy_status=None, is_for_kids=None)
        all_model: list[VideoModel] = []
        
        vm_builder: VideoModelBuilder = VideoModelBuilder()
        for data in all_data:
          all_model.append(self.parse(vm_builder, data))

        return all_model

    def find(self, id):
        data: dict[str, object] = self.context.read(id, 'file', file=None, title=None, description=None, category=None, keywords=None, privacy_status=None, is_for_kids=None)
        vm_builder: VideoModelBuilder = VideoModelBuilder()
        return self.parse(vm_builder, data) if data is not None else None

    def update(self, model: VideoModel):
        return model if self.context.update(model.file, 'file', file=model.file, title=model.title, description=model.description, category=model.category, keywords=model.keywords, privacy_status=model.privacy_status, is_for_kids=model.is_for_kids) else None

    def remove(self, model: VideoModel):
        return model if self.context.delete(model.file, 'file', file=None, title=None, description=None, category=None, keywords=None, privacy_status=None, is_for_kids=None) else None

    def parse(self, vm_builder: VideoModelBuilder, data: dict[str, object]):
        vm_builder.file(data['file'])
        vm_builder.title(data['title'])
        vm_builder.description(data['description'])
        vm_builder.category(data['category'])
        vm_builder.keywords(data['keywords'])
        vm_builder.privacy_status(data['privacy_status'])
        vm_builder.is_for_kids(data['is_for_kids'])

        return vm_builder.build()