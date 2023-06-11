import sys
import os
import json
import time

from urllib.parse import urlparse

from selenium_pro import webdriver
from selenium_pro.webdriver.common.by import By
from selenium_pro.webdriver.common.keys import Keys

from yt15m.iface.uploader import Uploader
from yt15m.util.helper import *
from yt15m.model.video import VideoModel


class YoutubeWebUploader(Uploader):
    
    def __init__(self, auth_cookies_file, show_web_browser=False, chromedriver_file="chromedriver.exe") -> None:
        self.__requirements = {
            'auth_cookies_file': auth_cookies_file,
            'show_web_browser': show_web_browser,
            'chromedriver_file': chromedriver_file
        }

    def auth_service(self):
        opts = None

        auth_cookies_file = self.__requirements['auth_cookies_file']
        show_web_browser = self.__requirements['show_web_browser']
        chromedriver_file = self.__requirements['chromedriver_file']

        f = open(auth_cookies_file, 'r')
        data = f.read()
        f.close()
        
        if data.strip() == "":
            log(f"Authentication cookies file at '{auth_cookies_file}' is empty! Please copy your authentication cookies into that file (using 'EditThisCookie' plugin).")
            return None

        if not show_web_browser:
            opts = webdriver.ChromeOptions()
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-popup-blocking")
        
        driver = webdriver.Chrome(executable_path=chromedriver_file, options=opts)
        driver.get("https://youtube.com")

        # inject session cookie
        data = json.loads(data)
        for cookie in data:
            cookie.pop('sameSite')
            driver.add_cookie(cookie)
        
        # login validation to verify if cookie valid.
        driver.get("https://studio.youtube.com")
        domain = urlparse(driver.current_url).netloc
        
        if domain != "studio.youtube.com": # login failed
            driver.close()
            driver = None
            log("Authentication failed! Please check (or renew) your authentication cookies file...", False)

        return driver

    def upload_video(self, video_model: VideoModel):
        video_id = None
        
        # currently only know 1 category for gaming.
        # add more...
        video_category = 22
        video_category = self.__get_category_name(video_category)
        
        video_privacy_status = video_model.privacy_status.upper()
        
        is_file_not_exists = not os.path.exists(video_model.file)
        
        if is_file_not_exists:
            log("Please specify a valid file.", is_file_not_exists)
            return None

        prepare_time = 8
        sleep_time = 3
        max_retries = 1800 / sleep_time
        count_retries = 0
        has_attribute = lambda attr : True if attr is not None else False
        
        try:
            debug_text = "Upload video file."
            log(debug_text)
            self.context.get("https://studio.youtube.com")
            self.context.switch_to.alert.accept()
        except:
            pass
        
        try:
            time.sleep(prepare_time)

            debug_text = 'Click "Create" button (on top-right corner).'
            self.context.find_elements(By.XPATH, "//ytcp-button[@id='create-icon']")[0].click_pro()
            log(debug_text, True)

            debug_text = 'Click "Upload video" dropdown item.'
            self.context.find_elements(By.XPATH, "//tp-yt-paper-item[@id='text-item-0']")[0].click_pro()
            log(debug_text, True)

            debug_text = 'Input file path to input file field (on changed, this will trigger submit file automatically).'
            self.context.find_elements(By.XPATH, "//*[@id='content']/input[@name='Filedata']")[0].send_keys(video_model.file)
            log(debug_text, True)

            time.sleep(prepare_time)

            debug_text = 'Uploading...'
            # No error handling, need more research.
            xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[2]/div/div[1]/ytcp-video-upload-progress/tp-yt-iron-icon[@id='processing-badge']"
            processing_badge_el = self.context.find_elements(By.XPATH, xpath)[0]
            xpath = "/html/body/ytcp-uploads-dialog"
            uploads_dialog_el = self.context.find_elements(By.XPATH, xpath)[0]

            log(debug_text)
            while True:
                # Check if error occurred.
                if has_attribute(uploads_dialog_el.get_attribute('has-error')):
                    xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[2]/div/div[1]/ytcp-ve/div[1]"
                    err_short_msg = self.context.find_elements(By.XPATH, xpath)[0].text
                    debug_text = f"Error occurred! Message => \"{err_short_msg}\""
                    raise

                # If processing badge become blue, (hopefully) it means video uploaded and begin processing video.
                if processing_badge_el.value_of_css_property('fill') == "rgb(62, 166, 255)":
                    # Get self.youtube.video id.
                    log("Uploaded. Getting self.youtube.video id.", True)
                    video_id = self.context.find_elements(By.XPATH, "//*[@id='details']/ytcp-video-metadata-editor-sidepanel/ytcp-video-info/div/div[2]/div[1]/div[2]/span/a")[0].get_attribute('href')
                    break
                
                count_retries += 1
                if count_retries >= max_retries:
                    debug_text = f"Timeout! Retries has been reached maximum: {count_retries}"
                    raise

                time.sleep(sleep_time)

            debug_text = "Click title div text field."
            xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[1]/ytcp-social-suggestions-textbox/ytcp-form-input-container/div[1]/div[2]/div/ytcp-social-suggestion-input/div"
            #xpath = "//ytcp-social-suggestions-textbox[@id='title-textarea']/*[@id='container']/*[@id='outer']/*[@id='child-input']/*[@id='container-content']/*[@id='input']/*[@id='textbox']"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)

            # Type video title.
            debug_text = "Input video title."
            self.context.switch_to.active_element.send_keys(Keys.CONTROL, 'a')
            self.context.switch_to.active_element.send_keys(video_model.title)
            log(debug_text, True)

            # Click description div text field.
            debug_text = "Click description div text field."
            xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[2]/ytcp-video-description/div/ytcp-social-suggestions-textbox/ytcp-form-input-container/div[1]/div[2]/div/ytcp-social-suggestion-input/div"
            #xpath = "//ytcp-social-suggestions-textbox[@id='description-textarea']/*[@id='container']/*[@id='outer']/*[@id='child-input']/*[@id='container-content']/*[@id='input']/*[@id='textbox']"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)
            
            # Type video description.
            debug_text = "Input video description."
            self.context.switch_to.active_element.send_keys(video_model.description)
            log(debug_text, True)

            # Choose Made-For-Kids option by click radio button.
            debug_text = "Choose Made-For-Kids option by click radio button."
            if video_model.is_for_kids:
                xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[5]/ytkc-made-for-kids-select/div[4]/tp-yt-paper-radio-group/tp-yt-paper-radio-button[1]"
            else:
                xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[5]/ytkc-made-for-kids-select/div[4]/tp-yt-paper-radio-group/tp-yt-paper-radio-button[2]"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)

            # Click advance detail.
            debug_text = "Click advance detail."
            xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/div/ytcp-button"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)

            time.sleep(prepare_time)

            # Input keywords to input text field.
            debug_text = "Input keywords to input text field."
            xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-advanced/div[4]/ytcp-form-input-container/div[1]/div/ytcp-free-text-chip-bar/ytcp-chip-bar/div/input"
            self.context.find_elements(By.XPATH, xpath)[0].send_keys(video_model.keywords)
            log(debug_text, True)

            # Select video category.
            debug_text = "Select video category."
            xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-ve/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-advanced/div[9]/div[3]/ytcp-form-select/ytcp-select"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            xpath = f"/html/body/ytcp-text-menu/tp-yt-paper-dialog/tp-yt-paper-listbox/tp-yt-paper-item[@test-id='{video_category}']"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)

            # Go to the last step.
            debug_text = "Go to the last step."
            xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/div[1]/ytcp-animatable/ytcp-stepper/div/div[4]/button"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)

            time.sleep(prepare_time)

            # Select video privacy.
            debug_text = "Select video privacy."
            xpath = f"/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[1]/ytcp-uploads-review/div[2]/div[1]/ytcp-video-visibility-select/div[2]/tp-yt-paper-radio-group/tp-yt-paper-radio-button[@name='{video_privacy_status}']"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)

            # Submit video.
            debug_text = "Submit video."
            xpath = "/html/body/ytcp-uploads-dialog/tp-yt-paper-dialog/div/ytcp-animatable[2]/div/div[2]/ytcp-button[@id='done-button']"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)

            time.sleep(prepare_time)
        
            # Close video process dialog.
            debug_text = "Close video process dialog."
            xpath = "/html/body/ytcp-uploads-still-processing-dialog/ytcp-dialog/tp-yt-paper-dialog/div[3]/ytcp-button"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)

        except Exception as e:
            log(debug_text + " [FAILED]", False)
            log(e, False)  
        
        if video_id is not None:
            video_id = video_id.split('/')[-1]
            
        return video_id

    def rewrite_description(self, video_description: str, video_id: str, video_model: VideoModel):
        prepare_time = 6

        debug_text = ""
        result = False

        try:
            debug_text = "Rewrite video description."
            self.context.get(f"https://studio.youtube.com/video/{video_id}/edit")
            self.context.switch_to.alert.accept()
        except:
            pass

        try:
            time.sleep(prepare_time)
            xpath = "/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[10]/ytcp-video-details-section/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[2]/ytcp-video-description/div/ytcp-social-suggestions-textbox/ytcp-form-input-container/div[1]/div[2]/div/ytcp-social-suggestion-input/div"
            # xpath = "/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[10]/ytcp-video-details-section/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[2]/ytcp-social-suggestions-textbox/ytcp-form-input-container/div[1]/div[2]/div/ytcp-social-suggestion-input/div"
            el = self.context.find_elements(By.XPATH, xpath)[0]
            el.click_pro()
            el.send_keys(Keys.CONTROL, 'a')
            el.send_keys(video_description)
            log(debug_text, True)
            
            time.sleep(prepare_time)
            
            debug_text = "Click save button."
            xpath = "/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[10]/ytcp-video-details-section/ytcp-sticky-header/ytcp-entity-page-header/div/div[2]/ytcp-button[@id='save']"
            el = self.context.find_elements(By.XPATH, xpath)[0]
            el.click_pro()
            log(debug_text, True)

            sleep_time = 3
            max_retries = 1800 / sleep_time
            count_retries = 0
            has_attribute = lambda attr : True if attr is not None else False
            while True:
                # If button become gray (disabled) from blue (active), it means done (hopefully).
                if has_attribute(el.value_of_css_property('disabled')):
                    log("Rewritten.", True)            
                    result = True
                    break
                
                count_retries += 1
                if count_retries >= max_retries:
                    debug_text = f"Timeout! Retries has been reached maximum: {count_retries}"
                    raise

                time.sleep(sleep_time)

        except Exception as e:
            log(debug_text + " [FAILED]", False)
            log(e, False)

        return result

    def add_video_to_playlist(self, playlist_id: str, video_id: str):
        prepare_time = 6

        debug_text = ""
        result = False

        try:
            debug_text = "Add video to playlist."
            self.context.get(f"https://studio.youtube.com/video/{video_id}/edit")
            self.context.switch_to.alert.accept()
        except:
            pass

        try:
            time.sleep(prepare_time)

            xpath = "/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[10]/ytcp-video-details-section/ytcp-video-metadata-editor/div/ytcp-video-metadata-editor-basics/div[4]/div[3]/div[1]/ytcp-video-metadata-playlists/ytcp-text-dropdown-trigger"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)

            debug_text = "Choose playlist."
            xpath = f"/html/body/ytcp-playlist-dialog/tp-yt-paper-dialog/ytcp-checkbox-group/div/ul/tp-yt-iron-list/div/ytcp-ve/li/label/ytcp-checkbox-lit[@test-id='{playlist_id}']"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)

            debug_text = "Click done button."
            xpath = "/html/body/ytcp-playlist-dialog/tp-yt-paper-dialog/div[2]/ytcp-button[@class='done-button action-button style-scope ytcp-playlist-dialog']"
            self.context.find_elements(By.XPATH, xpath)[0].click_pro()
            log(debug_text, True)

            time.sleep(prepare_time)
            
            debug_text = "Click save button."
            xpath = "/html/body/ytcp-app/ytcp-entity-page/div/div/main/div/ytcp-animatable[10]/ytcp-video-details-section/ytcp-sticky-header/ytcp-entity-page-header/div/div[2]/ytcp-button[@id='save']"
            el = self.context.find_elements(By.XPATH, xpath)[0]
            el.click_pro()
            log(debug_text, True)

            sleep_time = 3
            max_retries = 1800 / sleep_time
            count_retries = 0
            has_attribute = lambda attr : True if attr is not None else False
            while True:
                # If button become gray (disabled) from blue (active), it means done (hopefully).
                if has_attribute(el.value_of_css_property('disabled')):
                    log("Added.", True)            
                    result = True
                    break
                
                count_retries += 1
                if count_retries >= max_retries:
                    debug_text = f"Timeout! Retries has been reached maximum: {count_retries}"
                    raise

                time.sleep(sleep_time)

        except Exception as e:
            log(debug_text + " [FAILED]", False)
            log(e, False)
        
        return result

    def __get_category_name(self, category_id):
        video_category = ""
        
        if category_id == 22:
            video_category = "CREATOR_VIDEO_CATEGORY_GADGETS"
        
        return video_category