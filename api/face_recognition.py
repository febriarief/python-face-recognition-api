from rest_framework.response import Response
from rest_framework.decorators import api_view
from env.firebase import firebaseConfig
from PIL import Image
import pyrebase, requests, uuid, os, face_recognition.proccess as process, mimetypes

firebase = pyrebase.initialize_app(firebaseConfig)
storage  = firebase.storage()

SAMPLE_IMAGE_PATH = "storages/images/"

@api_view(['GET'])
def checkLiveness(request):
    try:
        if 'url' not in request.GET:
            return Response({ "status": 200, "data": {}, "message": "" }, status=200)
        
        url = request.GET['url']
        response = requests.get(url)

        guessImage = is_url_image(url)
        if guessImage != True:
            return Response({ "status": 422, "data": {}, "message": "Tidak ada gambar ditemukan di URL yang diberikan" }, status=422)
        
        if response.status_code != 200:
            return Response({ "status": 422, "data": {}, "message": "Gagal mendownload gambar" }, status=422)
        
        randString = str(uuid.uuid4())
        originalFilename = randString + "-ORIGINAL.jpg"
        originalFilepath = "{}/{}".format(SAMPLE_IMAGE_PATH, originalFilename)
        compressedFilename = randString + "-COMPRESSED.jpg"
        compressedFilepath = "{}/{}".format(SAMPLE_IMAGE_PATH, compressedFilename)

        # Save original image to local storage
        with open(originalFilepath, "wb") as original_image:
            original_image.write(response.content)

        # Resize and save original image to local storage
        img = Image.open(originalFilepath)
        width = int(img.width * (500 / img.height))
        img.thumbnail((width, 500), Image.ANTIALIAS)
        img.save(compressedFilepath)

        # Upload all images (original & compressed) to firebase storage
        storage.child("tmp/" + originalFilename).put(originalFilepath)
        storage.child("tmp/" + compressedFilename).put(compressedFilepath)

        # Do check liveness of image
        processImage = process.liveness(compressedFilename)

        # Remove all uploaded images
        os.remove(originalFilepath)
        os.remove(compressedFilepath)

        return Response(processImage, status=processImage["status"])
    
    except Exception as e:
        return Response({ "status": 500, "data": {}, "message": str(e) }, status=500)

def is_url_image(url):    
    mimetype, encoding = mimetypes.guess_type(url)
    return (mimetype and mimetype.startswith('image'))