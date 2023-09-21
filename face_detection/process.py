import os
import cv2
import numpy as np
import warnings
import time

from face_detection.src.anti_spoof_predict import AntiSpoofPredict
from face_detection.src.generate_patches import CropImage
from face_detection.src.utility import parse_model_name

warnings.filterwarnings('ignore')

def check_image(image):
    height, width, channel = image.shape
    if width/height != 3/4:
        return { "status": 422, "message": "Gambar tidak sesuai. Rasio tinggi:lebar gambar harus 4:3", "data": {} }
    else:
        return { "status": 200, "message": "", "data": {} }

def liveness(filepath):
    model_dir = "face_detection/resources/anti_spoof_models"
    device_id = 0
    
    try:
        model_test = AntiSpoofPredict(device_id)
        image_cropper = CropImage()
        image = cv2.imread(filepath)
        # result = check_image(image)
        # if result["status"] is not 200:
        #     return result
        
        image_bbox = model_test.get_bbox(image)
        prediction = np.zeros((1, 3))
        test_speed = 0
        for model_name in os.listdir(model_dir):
            h_input, w_input, model_type, scale = parse_model_name(model_name)
            param = {
                "org_img": image,
                "bbox": image_bbox,
                "scale": scale,
                "out_w": w_input,
                "out_h": h_input,
                "crop": True,
            }
            if scale is None:
                param["crop"] = False
            img = image_cropper.crop(**param)
            start = time.time()
            prediction += model_test.predict(img, os.path.join(model_dir, model_name))
            test_speed += time.time()-start

        label = np.argmax(prediction)
        livenessResult = True if label == 1 else False
        value = prediction[0][label]/2
        livenessScore = round(value, 2)
        execTime = round(test_speed, 2)
        return { "status": 200, "message": "", "data": { "filepath": filepath, "liveness": livenessResult, "score": livenessScore, "exec_time": str(execTime) + ' seconds' } }
    
    except Exception as e:
        return { "status": 500, "message": str(e), "data": {} } 
