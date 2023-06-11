import os
import shutil
import subprocess
from yt15m.iface.editor import Editor

class FfmpegEditor(Editor):

    def __init__(self, ffmpeg_path='ffmpeg') -> None:
        super().__init__(ffmpeg_path)

    def split_equally(self, source_path, destination_path, segment_time="00:15:00") -> bool:
        pathname, extension = os.path.splitext(destination_path)
        destination_path = f"{pathname} %d{extension}"
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        cmd = [
            self.context, 
            "-i", source_path,
            "-f", "segment",
            "-map", "0",
            "-segment_time", segment_time,
            "-reset_timestamps", "1",
            "-c:v", "copy",
            "-c:a", "copy",
            destination_path
        ]
        
        result = subprocess.run(cmd, capture_output=True)

        print("\n")

        return True if result.returncode == 0 else False

    def draw_watermark(self, source_path, destination_path, watermark_image) -> bool:
        pathname, extension = os.path.splitext(destination_path)
        temp_path = f"{pathname}-wm{extension}"


        cmd = [
            self.context,
            "-y", 
            "-hwaccel", "cuda",
            "-hwaccel_output_format", "cuda",
            "-i", source_path,
            "-i", watermark_image,
            "-filter_complex",
            (
                f"[1:v]format=rgba,colorchannelmixer=aa=0.1[logo];" +
                f"[0:v]scale_cuda=w=0:h=0:format=yuv420p:interp_algo=lanczos,hwdownload[video];" +
                f"[video][logo]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2,fps=fps=60,format=yuv420p"
            ),
            "-c:v", "h264_nvenc",
            "-c:a", "copy",
            temp_path
        ]

        result = subprocess.run(cmd, capture_output=True)

        print("\n")

        if result.returncode == 0:
            shutil.move(temp_path, destination_path)
            return True
        else:
            return False