
import os
import subprocess
import json
from dotenv import load_dotenv, dotenv_values

from yt15m.model.video import *
from yt15m.repository.video import VideoRepository

from yt15m.util.helper import use_hook

import traceback as backtrack

PROGRESS_DONE = "Done"

def execute(cmd):
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True) as popen:
        for stdout_line in iter(popen.stdout.readline, ""):
            print(stdout_line, end="", flush=True)
        result = popen.stderr.readline()
        result = json.loads(result[2:-4])
        print(result)
        popen.wait()
        if result['error_code'] != '':
            raise Exception()


def execute_cmd(vm, verbose=False, cookie_login=None, chromedriver=None, show_wb=False):
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
        "--show-web-browser" if show_wb else "",
        "--cookie-login-path", cookie_login,
        "--chromedriver-path", chromedriver
    ]

    result = True
    try:
        execute(cmd)
    except:
        backtrack.print_exc()
        result = False
    
    return result

def check_list_datastore(set_list_datastore):
    ok = True
    list_datastore = []

    path_series = "./Series"
    template_series = "__template_dont_delete"
    path_template = os.path.join(path_series, template_series)
    os.makedirs(path_template, exist_ok=True)
    # Create 'counter.txt' template
    if not os.path.exists(os.path.join(path_template, "counter.txt")):
        f = open(os.path.join(path_template, "counter.txt"), mode='w')
        f.write("0")
        f.close()
    if not os.path.exists(os.path.join(path_template, "series.txt")):
        f = open(os.path.join(path_template, "series.txt"), mode='w')
        f.writelines([
            "TITLE", "=", '"Insert series title."', "\n",
            "DESCRIPTION", "=", '"Insert series description."', "\n",
            "CATEGORY", "=", '"Insert series category. (ex. 22 for game)"', "\n",
            "KEYWORDS", "=", '"Insert series keywords. (ex. keyword 1,keyword 2,...keyword n)"', "\n",
            "PLAYLIST", "=", '"Insert series youtube playlist id."', "\n",
            "PRIVACY", "=", '"public"', "\n",
            "FORKIDS", "=", '0'
        ])
        f.close()
    sources = os.path.join(path_template, 'sources')
    os.makedirs(sources, exist_ok=True)
    repo_series = VideoRepository(os.path.join(path_series, template_series), "data")

    path_single = "./Single"
    os.makedirs(path_single, exist_ok=True)
    repo_single = VideoRepository(path_single, "data")

    for repo in [repo_series, repo_single]:
        repo_dir = os.path.join(repo.context.store, repo.context.branch)
        if not os.path.exists(repo_dir):
            print(f"Datastore '{repo.context.store}' did not exists!")
            print(f"Creating datastore...", end="")
            builder = VideoModelBuilder()
            builder.file("")
            builder.title("")
            builder.category("")
            builder.description("")
            builder.keywords("")
            repo.add(builder.build())
            print("Done")
            print(f"Datastore location: {repo_dir}")
            print("Try to add some video data in datastore, then try again\n")
            
            ok = False
    
    if not ok:
        return False

    vm = repo_single.all()[0]
    if vm.title is not None:
        list_datastore.append(repo_single)

    # For series, fetch all repo except template
    for series in os.listdir(path_series):
        if series == template_series:
            continue
        else:
            series = os.path.abspath(os.path.join(path_series, series))
            repo = VideoRepository(series, 'data')
            list_datastore.append(repo)
            counter_f = open(os.path.join(series, 'counter.txt'), mode='r')
            counter_m = int(counter_f.readline())
            counter_f.close()
            series_m = dotenv_values(os.path.join(series, 'series.txt'))
            builder = None
            
            for model in repo.all():
                builder = VideoModelBuilder(model)
                if not model.title:
                    builder.title(f"{series_m['TITLE']} {counter_m}")
                    builder.file(os.path.join(series, 'sources', f"video{counter_m}.mp4"))
                    builder.description(series_m['DESCRIPTION'])
                    builder.category(series_m['CATEGORY'])
                    builder.keywords(series_m['KEYWORDS'])
                    builder.playlist(series_m['PLAYLIST'])
                    builder.privacy_status(series_m['PRIVACY'])
                    builder.is_for_kids(series_m['FORKIDS'])
                    counter_m += 1
                    repo.update(builder.build())
            
            counter_f = open(os.path.join(series, 'counter.txt'), mode='w')
            counter_f.write(str(counter_m))
            counter_f.close()

    set_list_datastore(list_datastore)
    return True

    


def main():
    load_dotenv()
    verbose = os.getenv('YT15M_VERBOSE') == '1'
    cookie_login = os.getenv('YT15M_UPLOADER_WEB_COOKIELOGIN')
    chromedriver = os.getenv('YT15M_UPLOADER_WEB_CHROMEDRIVER')
    show_wb = os.getenv('YT15M_UPLOADER_WEB_SHOWWEBBROWSER') == '1'

    list_datastore, set_list_datastore = use_hook()

    if check_list_datastore(set_list_datastore):
        builder = None
        for repo in list_datastore[0]:
            list_vm = repo.all()
            try:
                for vm in list_vm:
                    if vm.progress != PROGRESS_DONE:
                        print(f"Processing '{vm.title}'...")
                        if execute_cmd(vm, verbose=verbose, cookie_login=cookie_login, chromedriver=chromedriver, show_wb=show_wb):
                            builder = VideoModelBuilder(vm)
                            builder.progress(PROGRESS_DONE)
                            repo.update(builder.build())
                        else:
                            raise Exception()
            except:
                break
    pass

if __name__ == "__main__":
    main()
    pass
