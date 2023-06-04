from yt15m.iface.context import Context

class Editor(Context):

    def split_equally(self, source_path, destination_path, segment_time="00:15:00") -> bool:
        pass

    def draw_watermark(self, source_path, destination_path, watermark_image) -> bool:
        pass