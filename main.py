import os
import time

import io
import hashlib
import signal
from glob import glob
import requests

from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

number_of_images = 200
SKIP_RESULT = -1
GET_IMAGE_TIMEOUT = 2
SLEEP_BETWEEN_INTERACTIONS = 3
SLEEP_BEFORE_MORE = 30
IMAGE_QUALITY = 85
DRIVER_PATH="./chromedriver.exe"
output_path = "./image"

search_terms = ["yoga one person poses downdog"]

dirs = glob(output_path + "*")
dirs = [dir.split("/")[-1].replace("_", " ") for dir in dirs]
search_terms = [term for term in search_terms if term not in dirs]


class timeout:
  def __init__(self, seconds=1, error_message="Timeout"):
    self.seconds = seconds
    self.error_message = error_message

  def handle_timeout(self, signum, frame):
    raise TimeoutError(self.error_message)

  def __enter__(self):
    signal.signal(signal.SIGALRM, self.handle_timeout)
    signal.alarm(self.seconds)

  def __exit__(self, type, value, traceback):
    signal.alarm(0)

def updatable_print(string):
    print(string, end='\r')
    print('', end='', flush=True)

def document_initialised(driver):
    return driver.execute_script("return initialised")

def fetch_image_urls(
  query: str,
  max_links_to_fetch: int,
  wd: webdriver,
  sleep_between_interactions: int = 1,
):
  def scroll_to_end(wd):
    wd.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(sleep_between_interactions)

  # Build the Google Query.
  search_url = "https://www.google.com/search?safe=off&site=&&tbs=isz:l&tbm=isch&source=hp&q={q}&oq={q}&gs_l=img"

  # load the page
  wd.get(search_url.format(q=query))

  # Declared as a set, to prevent duplicates.
  image_urls = set()
  image_count = 0
  results_start = 0
  while image_count < max_links_to_fetch:
    time.sleep(sleep_between_interactions)
    scroll_to_end(wd)

    # Get all image thumbnail results
    thumbnail_results = wd.find_elements(By.CSS_SELECTOR,"img.Q4LuWd")
    number_results = len(thumbnail_results)

    print(
      f"Found: {number_results} search results. Extracting links from {results_start}:{number_results}"
    )
    if results_start >= number_results:
      print("Something went wrong, stop.")
      return image_urls

    if(results_start < SKIP_RESULT):
      results_start = len(thumbnail_results)
      print("skip")

    # Loop through image thumbnail identified
    for n, img in enumerate(thumbnail_results[results_start:number_results]):
      updatable_print(f'Extract {n+results_start}/{number_results} results')
      # Try to click every thumbnail such that we can get the real image behind it.
      try:
        img.click()
      except Exception:
        continue

      try:
        WebDriverWait(wd, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "img.n3VNCb.KAlRDb") ))
        # WebDriverWait(wd, 100).until(EC.all_of(
        #   EC.attributeContains((By.CSS_SELECTOR, "img.n3VNCb") ),
        #   EC.text_to_be_present_in_element_attribute((By.CSS_SELECTOR, "img.n3VNCb"),"src","http")
        #   ))
      except:
        pass

      # Extract image urls

      actual_images = wd.find_elements(By.CSS_SELECTOR,"img.n3VNCb")
      
      for actual_image in actual_images:
        image_src = actual_image.get_attribute("src")
        if image_src and "http" in image_src and "encrypted-tbn0.gstatic.com" not in image_src:
          image_urls.add(image_src)

    image_count = len(image_urls)

    # If the number images found exceeds our `num_of_images`, end the seaerch.
    if image_count >= max_links_to_fetch:
      print(f"Found: {len(image_urls)} image links, done!")
      break
    else:
      # If we haven't found all the images we want, let's look for more.
      print("Found:", len(image_urls), "image links, looking for more ...")
      time.sleep(SLEEP_BEFORE_MORE)
      scroll_to_end(wd)
      # Check for button signifying no more images.
      not_what_you_want_button = ""
      try:
        not_what_you_want_button = wd.find_element_by_css_selector(".r0zKGf")
      except:
        pass

      # If there are no more images return.
      if not_what_you_want_button:
        print("No more images available.")
        return image_urls

      # If there is a "Load More" button, click it.
      load_more_button = wd.find_element(By.CSS_SELECTOR,".mye4qd")
      if load_more_button and not not_what_you_want_button:
        wd.execute_script("document.querySelector('.mye4qd').click();")
        time.sleep(SLEEP_BEFORE_MORE)

    # Move the result startpoint further down.
    results_start = len(thumbnail_results)

  return image_urls


def persist_image(folder_path: str, url: str):
  try:
    print("Getting image")
    # Download the image.  If timeout is exceeded, throw an error.
    with timeout(GET_IMAGE_TIMEOUT):
      image_content = requests.get(url).content

  except Exception as e:
    print(f"ERROR - Could not download {url} - {e}")

  try:
    # Convert the image into a bit stream, then save it.
    image_file = io.BytesIO(image_content)
    image = Image.open(image_file).convert("RGB")
    # Create a unique filepath from the contents of the image.
    file_path = os.path.join(
      folder_path, hashlib.sha1(image_content).hexdigest()[:10] + ".jpg"
    )
    with open(file_path, "wb") as f:
      image.save(f, "JPEG", quality=IMAGE_QUALITY)
    print(f"SUCCESS - saved {url} - as {file_path}")
  except Exception as e:
    print(f"ERROR - Could not save {url} - {e}")

def write_strings_to_file(strings, file_path):
    with open(file_path, "w") as f:
        for string in strings:
            f.write(string + "\n")

def search_and_download(search_term: str, target_path="./images", number_images=5):
  # Create a folder name.
  target_folder = os.path.join(target_path, "_".join(search_term.lower().split(" ")))

  # Create image folder if needed.
  if not os.path.exists(target_folder):
    os.makedirs(target_folder)

  # Open Chrome
  options = webdriver.ChromeOptions()
  options.add_experimental_option('excludeSwitches', ['enable-logging'])
  with webdriver.Chrome(service=Service(DRIVER_PATH),options=options) as wd:
    # Search for images URLs.
    res = fetch_image_urls(
      search_term,
      number_images,
      wd=wd,
      sleep_between_interactions=SLEEP_BETWEEN_INTERACTIONS,
    )

    # Download the images.
    write_strings_to_file(res,"images.txt")
    # if res is not None:
    #   for elem in res:
    #     # persist_image(target_folder, elem)
    #     print(res)
    # else:
    #   print(f"Failed to return links for term: {search_term}")

# Loop through all the search terms.
for term in search_terms:
  search_and_download(term, output_path, number_of_images)
