import requests
from PIL import Image
from io import BytesIO
from urllib.parse import urlsplit
import os

OUTPUT_PATH="./images/"

def image_name_gen(img_path):
  result = urlsplit(img_path)
  image_name = result.path.split("/")[-1]
  image_name_without_extension = os.path.splitext(image_name)[0]
  new_image_name = f"{image_name_without_extension}.jpg"
  return new_image_name

def downloadImage(img_path):
  
  try:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36', "Upgrade-Insecure-Requests": "1","DNT": "1","Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language": "en-US,en;q=0.5","Accept-Encoding": "gzip, deflate"}
    response = requests.get(img_path,headers=headers)
    image_name = image_name_gen(img_path)
    img = Image.open(BytesIO(response.content))
    img.save(OUTPUT_PATH + image_name, 'JPEG')
    return 1;
  except :
    return 0;

def main():
  with open("images1.txt") as f:
    image_paths = f.read().splitlines()
  for image_path in image_paths:
    res = downloadImage(image_path)
    if res == 0:
      print("Download Fail!")

main()