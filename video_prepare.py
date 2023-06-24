
import os
import subprocess
import json
from dotenv import load_dotenv

from yt15m.model.video import *
from yt15m.repository.video import VideoRepository

PROGRESS_DONE = "Done"

def execute(cmd):
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True) as popen:
        for stdout_line in iter(popen.stdout.readline, ""):
            print(stdout_line, end="", flush=True)
        result = json.loads(popen.stderr.readline)
        popen.wait()
        if result['error_code'] != '':
            raise Exception()


def execute_cmd(vm, verbose=False, cookie_login=None, chromedriver=None):
    cmd = [
        #"venv\\Scripts\\activate.bat", "&&",
        "python", "video_pipeline.py",
        "-v" if verbose else "",
        "--video-file", str(vm.file),
        "--video-title", str(vm.title),
        "--video-category", str(vm.category),
        "--video-description", str(vm.description),
        "--video-keywords", str(vm.keywords),
        "--video-privacy", str(vm.privacy_status),
        "--video-for-kids", str(vm.is_for_kids),
        "--video-playlist", str(vm.playlist),
        "--video-vid", str(vm.vid),
        "--video-progress", str(vm.progress),
        "--uploader", 'web',
        "--cookie-login-path", cookie_login,
        "--chromedriver-path", chromedriver,
        "--show-web-browser"
    ]

    result = True
    try:
        execute(cmd)
    except:
        result = False
    
    return result

def main():
    load_dotenv()
    verbose = os.getenv('YT15M_VERBOSE') == '1'
    cookie_login = os.getenv('YT15M_UPLOADER_WEB_COOKIELOGIN')
    chromedriver = os.getenv('YT15M_UPLOADER_WEB_CHROMEDRIVER')
    repo = VideoRepository("./", "data")
    repo_dir = os.path.join(repo.context.store, repo.context.branch)

    if not os.path.exists(repo_dir):
        print("Datastore did not exists!")
        print("Creating datastore...", end="")
        builder = VideoModelBuilder()
        builder.file("")
        builder.title("")
        builder.category("")
        builder.description("")
        builder.keywords("")
        repo.add(builder.build())
        print("Done")
        print(f"Datastore location: {repo_dir}")
        print("Try to add some video data in datastore, then try again")
    else:
        builder = None
        list_vm = repo.all()
        for vm in list_vm:
            if vm.progress != PROGRESS_DONE:
                if execute_cmd(vm, verbose=verbose, cookie_login=cookie_login, chromedriver=chromedriver):
                    builder = VideoModelBuilder(vm)
                    builder.progress(PROGRESS_DONE)
                    repo.update(builder.build())
                else:
                    break
    pass

if __name__ == "__main__":
    main()
    pass
