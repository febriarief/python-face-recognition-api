from django.conf import settings
from PIL import Image
from env.firebase import firebaseConfig
from . import utils
import requests, uuid, os, pyrebase, traceback

firebase = pyrebase.initialize_app(firebaseConfig)
storage  = firebase.storage()

def compress_image(image_url):
    response = requests.get(image_url, verify=False)   
    if response.status_code != 200:
        return { "status": 422, "data": {}, "message": "Gagal mendownload gambar dari {}".format(image_url) }
    
    content_type = response.headers.get("content-type")
    if not (content_type and content_type.startswith("image")):
        return { "status": 422, "data": {}, "message": "Url {} tidak mengandung MIME gambar".format(image_url) }
    
    compressed_image_path = settings.STORAGE_ROOT + "/images"
    random_string = str(uuid.uuid4())
    original_filename = random_string + "-ORIGINAL.jpg"
    original_filepath = "{}/{}".format(compressed_image_path, original_filename)
    compressed_filename = random_string + "-COMPRESSED.jpg"
    compressed_filepath = "{}/{}".format(compressed_image_path, compressed_filename)

    with open(original_filepath, "wb") as original_image:
        original_image.write(response.content)

    img = Image.open(original_filepath)
    width = int(img.width * (200 / img.height))
    img.thumbnail((width, 200), Image.ANTIALIAS)
    img.save(compressed_filepath)

    # Remove original image
    os.remove(original_filepath)

    return { "status": 200, "filename": compressed_filename, "filepath": compressed_filepath }

def upload_image(filename, filepath):
    try:
        storage.child("tmp/" + filename).put(filepath)
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        utils.create_log(traceback.format_exc())
