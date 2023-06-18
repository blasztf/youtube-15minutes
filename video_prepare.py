
import os
import subprocess

from yt15m.model.video import *
from yt15m.repository.video import VideoRepository

PROGRESS_DONE = "Done"

def execute(cmd):
    popen = subprocess.Popen(cmd, stdout=subprocess.PIPE, universal_newlines=True)
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line 
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)

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
        "--cookie-login-path", cookie_login,
        "--chromedriver-path", chromedriver,
        "--show-web-browser"
    ]

    for line in execute(cmd):
        print(line, end="")

    pass

def main():
    verbose = True
    cookie_login = ""
    chromedriver = ""
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
        list_vm = repo.all()
        for vm in list_vm:
            execute_cmd(vm, verbose=verbose, cookie_login=cookie_login, chromedriver=chromedriver)
    pass

if __name__ == "__main__":
    main()
    pass
