import sys
import os
import json
import time

from urllib.parse import urlparse

from selenium_pro import webdriver
from selenium_pro.webdriver.common.by import By
from selenium_pro.webdriver.common.keys import Keys

from yt15m.__bak__ import helper

def init_youtube(auth_cookies_file, show_web_browser=False, chromedriver_file="chromedriver.exe", **kwargs):
    opts = None

    f = open(auth_cookies_file, 'r')
    data = f.read()
    f.close()

    if data.strip() == "":
        helper.log(f"Authentication cookies file at '{auth_cookies_file}' is empty! Please copy your authentication cookies into that file (using 'EditThisCookie' plugin).")
        return None

    driver = None
    if not show_web_browser:
        opts = webdriver.ChromeOptions()
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-popup-blocking")
        driver = webdriver.Chrome(executable_path=chromedriver_file, options=opts)
    else:
        driver = webdriver.Chrome(executable_path=chromedriver_file)
    
    driver.get("https://youtube.com")

    # inject session cookie
    data = json.loads(data)
    for cookie in data:
        cookie.pop('sameSite')
        driver.add_cookie(cookie)

    # add login check to verify if cookie valid.
    
    driver.get("https://studio.youtube.com")
    domain = urlparse(driver.current_url).netloc
    if domain != "studio.youtube.com": # login failed
        driver.close()
        driver = None
        helper.log("Authentication failed! Please check (or renew) your authentication cookies file...", False)

    return driver
    

def upload_video(youtube, video_file, video_title, video_category, video_description, video_keywords, video_privacy_status="public", video_is_for_kids=False, **kwargs):
    video_id = None
    
    # currently only know 1 category for gaming.
    # add more...
    video_category = 22
    video_category = __get_category_name(video_category)
    
    video_privacy_status = video_privacy_status.upper()

    is_file_not_exists = not os.path.exists(video_file)

    if is_file_not_exists:
        helper.log("Please specify a valid file.", is_file_not_exists)
        return None

    prepare_time = 8
    sleep_time = 3
    max_retries = 1800 / sleep_time
    count_retries = 0
    has_attribute = lambda attr : True if attr is not None else False

    try:
        debug_text = "Upload video file."
        helper.log(debug_text)
        youtube.get("https://studio.youtube.com")
        youtube.switch_to.alert.accept()
    except:
        pass
    
    try:
        time.sleep(prepare_time)

        debug_text = 'Click "Create" button (on top-right corner).'
        youtube.find_elements(By.XPATH, "//ytcp-button[@id='create-icon']")[0].click_pro()
        helper.log(debug_text, True)

        debug_text = 'Click "Upload video" dropdown item.'
        youtube.find_elements(By.XPATH, "//tp-yt-paper-item[@id='text-item-0']")[0].click_pro()
        helper.log(debug_text, True)

        debug_text = 'Input file path to input file field (on changed, this will trigger submit file automatically).'
        youtube.find_elements(By.XPATH, "//*[@id='content']/input[@name='Filedata']")[0].send_keys(video_file)
        helper.log(debug_text, True)

        time.sleep(prepare_time)

        debug_text = 'Uploading...'
        # No error handling, need more research.
        xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[2]/div/div[1]/ytcp-video-upload-progress/tp-yt-iron-icon[@id='processing-badge']"
        processing_badge_el = youtube.find_elements(By.XPATH, xpath)[0]
        xpath = "/html/body/ytcp-uploads-dialog"
        uploads_dialog_el = youtube.find_elements(By.XPATH, xpath)[0]

        helper.log(debug_text)
        while True:
            # Check if error occurred.
            if has_attribute(uploads_dialog_el.get_attribute('has-error')):
                xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[2]/div/div[1]/ytcp-ve/div[1]"
                err_short_msg = youtube.find_elements(By.XPATH, xpath)[0].text
                debug_text = f"Error occurred! Message => \"{err_short_msg}\""
                raise

            # If processing badge become blue, (hopefully) it means video uploaded and begin processing video.
            if processing_badge_el.value_of_css_property('fill') == "rgb(62, 166, 255)":
                # Get youtube video id.
                helper.log("Uploaded. Getting youtube video id.", True)
                video_id = youtube.find_elements(By.XPATH, "//*[@id='details']/ytcp-video-metadata-editor-sidepanel/ytcp-video-info/div/div[2]/div[1]/div[2]/span/a")[0].get_attribute('href')
                break
            
            count_retries += 1
            if count_retries >= max_retries:
                debug_text = f"Timeout! Retries has been reached maximum: {count_retries}"
                raise

            time.sleep(sleep_time)

        debug_text = "Click title div text field."
        xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[1]/ytcp-social-suggestions-textbox/ytcp-form-input-container/div[1]/div[2]/div/ytcp-social-suggestion-input/div"
        #xpath = "//ytcp-social-suggestions-textbox[@id='title-textarea']/*[@id='container']/*[@id='outer']/*[@id='child-input']/*[@id='container-content']/*[@id='input']/*[@id='textbox']"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)

        # Type video title.
        debug_text = "Input video title."
        youtube.switch_to.active_element.send_keys(Keys.CONTROL, 'a')
        youtube.switch_to.active_element.send_keys(video_title)
        helper.log(debug_text, True)

        # Click description div text field.
        debug_text = "Click description div text field."
        xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[2]/ytcp-video-description/div/ytcp-social-suggestions-textbox/ytcp-form-input-container/div[1]/div[2]/div/ytcp-social-suggestion-input/div"
        #xpath = "//ytcp-social-suggestions-textbox[@id='description-textarea']/*[@id='container']/*[@id='outer']/*[@id='child-input']/*[@id='container-content']/*[@id='input']/*[@id='textbox']"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)
        
        # Type video description.
        debug_text = "Input video description."
        youtube.switch_to.active_element.send_keys(video_description)
        helper.log(debug_text, True)

        # Choose Made-For-Kids option by click radio button.
        debug_text = "Choose Made-For-Kids option by click radio button."
        if video_is_for_kids:
            xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[5]/ytkc-made-for-kids-select/div[4]/tp-yt-paper-radio-group/tp-yt-paper-radio-button[1]"
        else:
            xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[5]/ytkc-made-for-kids-select/div[4]/tp-yt-paper-radio-group/tp-yt-paper-radio-button[2]"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)

        # Click advance detail.
        debug_text = "Click advance detail."
        xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/div/ytcp-button"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)

        time.sleep(prepare_time)

        # Input keywords to input text field.
        debug_text = "Input keywords to input text field."
        xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-advanced/div[4]/ytcp-form-input-container/div[1]/div/ytcp-free-text-chip-bar/ytcp-chip-bar/div/input"
        youtube.find_elements(By.XPATH, xpath)[0].send_keys(video_keywords)
        helper.log(debug_text, True)

        # Select video category.
        debug_text = "Select video category."
        xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-advanced/div[9]/div[3]/ytcp-form-select/ytcp-select"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        xpath = f"/html/body/ytcp-text-menu/tp-yt-paper-dialog/tp-yt-paper-listbox/tp-yt-paper-item[@test-id='{video_category}']"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)

        # Go to the last step.
        debug_text = "Go to the last step."
        xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/div[1]/ytcp-animatable/ytcp-stepper/div/div[4]/button"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)

        time.sleep(prepare_time)

        # Select video privacy.
        debug_text = "Select video privacy."
        xpath = f"/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-uploads-review/div[2]/div[1]/ytcp-video-visibility-select/div[2]/tp-yt-paper-radio-group/tp-yt-paper-radio-button[@name='{video_privacy_status}']"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)

        # Submit video.
        debug_text = "Submit video."
        xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[2]/div/div[2]/ytcp-button[@id='done-button']"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)

        time.sleep(prepare_time)
    
        # Close video process dialog.
        debug_text = "Close video process dialog."
        xpath = "/html/body/ytcp-uploads-still-processing-dialog/ytcp-dialog/tp-yt-paper-dialog/div[3]/ytcp-button"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)

    except Exception as e:
        helper.log(debug_text + " [FAILED]", False)
        helper.log(e, False)  
    
    if video_id is not None:
        video_id = video_id.split('/')[-1]
        
    return video_id
    
def rewrite_description(youtube, video_id, video_description, **kwargs):
    prepare_time = 6

    debug_text = ""
    result = False

    try:
        debug_text = "Rewrite video description."
        youtube.get(f"https://studio.youtube.com/video/{video_id}/edit")
        youtube.switch_to.alert.accept()
    except:
        pass

    try:
        time.sleep(prepare_time)
        xpath = "/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[10]/ytcp-video-details-section/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[2]/ytcp-video-description/div/ytcp-social-suggestions-textbox/ytcp-form-input-container/div[1]/div[2]/div/ytcp-social-suggestion-input/div"
        # xpath = "/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[10]/ytcp-video-details-section/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[2]/ytcp-social-suggestions-textbox/ytcp-form-input-container/div[1]/div[2]/div/ytcp-social-suggestion-input/div"
        el = youtube.find_elements(By.XPATH, xpath)[0]
        el.click_pro()
        el.send_keys(Keys.CONTROL, 'a')
        el.send_keys(video_description)
        helper.log(debug_text, True)
        
        time.sleep(prepare_time)
        
        debug_text = "Click save button."
        xpath = "/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[10]/ytcp-video-details-section/ytcp-sticky-header/ytcp-entity-page-header/div/div[2]/ytcp-button[@id='save']"
        el = youtube.find_elements(By.XPATH, xpath)[0]
        el.click_pro()
        helper.log(debug_text, True)

        sleep_time = 3
        max_retries = 1800 / sleep_time
        count_retries = 0
        has_attribute = lambda attr : True if attr is not None else False
        while True:
            # If button become gray (disabled) from blue (active), it means done (hopefully).
            if has_attribute(el.value_of_css_property('disabled')):
                helper.log("Rewritten.", True)            
                result = True
                break
            
            count_retries += 1
            if count_retries >= max_retries:
                debug_text = f"Timeout! Retries has been reached maximum: {count_retries}"
                raise

            time.sleep(sleep_time)

    except Exception as e:
        helper.log(debug_text + " [FAILED]", False)
        helper.log(e, False)

    return result

def add_playlist_item(youtube, playlist_id, video_id, **kwargs):
    prepare_time = 6

    debug_text = ""
    result = False

    try:
        debug_text = "Add video to playlist."
        youtube.get(f"https://studio.youtube.com/video/{video_id}/edit")
        youtube.switch_to.alert.accept()
    except:
        pass

    try:
        time.sleep(prepare_time)

        xpath = "/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[10]/ytcp-video-details-section/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[4]/div[3]/div[1]/ytcp-video-metadata-playlists/ytcp-text-dropdown-trigger"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)

        debug_text = "Choose playlist."
        xpath = f"/html/body/ytcp-playlist-dialog/tp-yt-paper-dialog/ytcp-checkbox-group/div/ul/tp-yt-iron-list/div/ytcp-ve/li/label/ytcp-checkbox-lit[@test-id='{playlist_id}']"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)

        debug_text = "Click done button."
        xpath = "/html/body/ytcp-playlist-dialog/tp-yt-paper-dialog/div[2]/ytcp-button[@class='done-button action-button style-scope ytcp-playlist-dialog']"
        youtube.find_elements(By.XPATH, xpath)[0].click_pro()
        helper.log(debug_text, True)

        time.sleep(prepare_time)
        
        debug_text = "Click save button."
        xpath = "/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[10]/ytcp-video-details-section/ytcp-sticky-header/ytcp-entity-page-header/div/div[2]/ytcp-button[@id='save']"
        el = youtube.find_elements(By.XPATH, xpath)[0]
        el.click_pro()
        helper.log(debug_text, True)

        sleep_time = 3
        max_retries = 1800 / sleep_time
        count_retries = 0
        has_attribute = lambda attr : True if attr is not None else False
        while True:
            # If button become gray (disabled) from blue (active), it means done (hopefully).
            if has_attribute(el.value_of_css_property('disabled')):
                helper.log("Added.", True)            
                result = True
                break
            
            count_retries += 1
            if count_retries >= max_retries:
                debug_text = f"Timeout! Retries has been reached maximum: {count_retries}"
                raise

            time.sleep(sleep_time)

    except Exception as e:
        helper.log(debug_text + " [FAILED]", False)
        helper.log(e, False)
    
    return result

def __get_category_name(category_id):
    video_category = ""
    
    if category_id == 22:
        video_category = "CREATOR_VIDEO_CATEGORY_GADGETS"
    
    return video_category