from rest_framework.decorators import api_view
from rest_framework.response import Response
from api.serializers import LivenessLogsSerializer, CompareLogsSerializer
from . import image_processing
from . import utils
import concurrent.futures, face_comparison.process as face_compare, face_detection.process as FaceDetection, math, os, time, traceback

@api_view(["GET"])
def index(request):
    return Response({ "status": 200, "data": {}, "message": "Hello" }, status=200)

def validate_process_request(request):
    post_data = request.data

    if "type" not in post_data or post_data["type"] not in ["liveness", "compare", "both"]:
        return { "status": 422, "data": {}, "message": "Invalid param type" }
    
    # Only liveness
    if post_data["type"] == "liveness" :
        if "filepath" not in post_data:
            return { "status": 422, "data": {}, "message": "Kolom filepath tidak boleh kosong" }
        
    # Face compare and check liveness
    if post_data["type"] == "compare" or post_data["type"] == "both":
        if "filepath_1" not in post_data:
            return { "status": 422, "data": {}, "message": "Kolom filepath_1 tidak boleh kosong" }
        
        if "filepath_2" not in post_data:
            return { "status": 422, "data": {}, "message": "Kolom filepath_2 tidak boleh kosong" }

    
    return { "status": 200, "data": {}, "message": "" }

@api_view(["POST"])
def process(request):
    validate = validate_process_request(request)
    if validate["status"] != 200:
        return Response(validate, status=validate["status"])
    
    post_data = request.data

    # Handle only liveness detection
    if post_data["type"] == "liveness":
        filepath = post_data["filepath"]
        liveness = check_liveness(filepath)
        return Response(liveness, status=liveness["status"])    

    # Handle only face compare
    if post_data["type"] == "compare":
        filepath_1 = post_data["filepath_1"]
        filepath_2 = post_data["filepath_2"]
        compare_image = compare(filepath_1, filepath_2)
        return Response(compare_image, status=compare_image["status"])
    
    # Handle face compare and liveness
    if post_data["type"] == "both":
        filepath_1 = post_data["filepath_1"]
        filepath_2 = post_data["filepath_2"]
        compare_and_liveness_image = compare_and_liveness(filepath_1, filepath_2)
        return Response(compare_and_liveness_image, status=compare_and_liveness_image["status"])

    return Response({ "status": 200, "data": {}, "message": "Hello" }, status=200)

def check_liveness(image_url, is_compare_and_liveness=False):
    start_time = time.time()

    try:
        if is_compare_and_liveness == False:
            compressed_image = image_processing.compress_image(image_url)
            if compressed_image["status"] != 200:
                return compressed_image
            
            filename = compressed_image["filename"]
            filepath = compressed_image["filepath"]
        else:
            filename = image_url["filename"]
            filepath = image_url["filepath"]

        liveness = FaceDetection.liveness(filepath)
        if liveness["status"] != 200:
            if os.path.exists(filepath):
                os.remove(filepath)

            return liveness

        exec_time = round(time.time() - start_time, 2)
        response_data = {
            "filename": filename,
            "score": liveness["data"]["score"],
            "result": liveness["data"]["liveness"],
            "exec_time": "{} second".format(exec_time),
            "message": liveness["message"]
        }

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(save_log_liveness, response_data)
            
            if is_compare_and_liveness == False:
                executor.submit(image_processing.upload_image, filename, filepath)

        return { "status": 200, "data": response_data, "message": "" }

    except Exception as e:
        utils.create_log(traceback.format_exc())
        return { "status": 500, "data": {}, "message": str(e) }

def save_log_liveness(data):
    liveness_logs_serializer = LivenessLogsSerializer(data=data)
    if liveness_logs_serializer.is_valid():
        liveness_logs_serializer.save()
    else:
        utils.create_log(liveness_logs_serializer.errors)

def compare(image_url_1, image_url_2, is_compare_and_liveness=False):
    start_time = time.time()

    try:
        if is_compare_and_liveness == False:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                compress_future_1 = executor.submit(image_processing.compress_image, image_url_1)
                compress_future_2 = executor.submit(image_processing.compress_image, image_url_2)
                
                concurrent.futures.wait([compress_future_1, compress_future_2])
                
                compressed_image_1 = compress_future_1.result()
                compressed_image_2 = compress_future_2.result()

                if compressed_image_1["status"] != 200 or compressed_image_2["status"] != 200:
                    if "filepath" in compressed_image_1 and os.path.exists(compressed_image_1["filepath"]):
                        os.remove(compressed_image_1["filepath"])

                    if "filepath" in compressed_image_2 and os.path.exists(compressed_image_2["filepath"]):
                        os.remove(compressed_image_2["filepath"])

                    return { "status": 500, "data": {}, "message": "Gagal melakukan kompresi gambar" }

                compressed_filename_1 = compressed_image_1["filename"]
                compressed_filepath_1 = compressed_image_1["filepath"]
                compressed_filename_2 = compressed_image_2["filename"]
                compressed_filepath_2 = compressed_image_2["filepath"]
        else:
            compressed_filename_1 = image_url_1["filename"]
            compressed_filepath_1 = image_url_1["filepath"]
            compressed_filename_2 = image_url_2["filename"]
            compressed_filepath_2 = image_url_2["filepath"]
            
        face_distances = face_compare.faceDistance(compressed_filepath_1, compressed_filepath_2)
        tolerance = 0.4
        distance = 0
        for i, face_distance in enumerate(face_distances):
            face_distance = math.floor(face_distance * 10) / 10
            result = False

            if (face_distance == 0):
                result = False
            elif (face_distance <= tolerance):
                result = True
            else:
                result = False

            distance = face_distance

        exec_time = round(time.time() - start_time, 2)
        response_data = {
            "filename_1"    : compressed_filename_1,
            "filename_2"    : compressed_filename_2,
            "face_distance" : distance,
            "tolerance"     : tolerance,
            "result"        : result,
            "message"       : "",
            "exec_time"     : "{} second".format(exec_time)
        }

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(save_log_compare, response_data)

            if is_compare_and_liveness == False:
                executor.submit(image_processing.upload_image, compressed_filename_1, compressed_filepath_1)
                time.sleep(3)
                executor.submit(image_processing.upload_image, compressed_filename_2, compressed_filepath_2)
        
        return { "status": 200, "data": response_data, "message": "" }

    except Exception as e:
        if compressed_filepath_1 is not None and os.path.exists(compressed_filepath_1):
            os.remove(compressed_filepath_1)

        if compressed_filepath_2 is not None and os.path.exists(compressed_filepath_2):
            os.remove(compressed_filepath_2)

        utils.create_log(traceback.format_exc())
        return { "status": 500, "data": {}, "message": str(e) }

def save_log_compare(data):
    compare_logs_serializer = CompareLogsSerializer(data=data)
    if compare_logs_serializer.is_valid():
        compare_logs_serializer.save()
    else:
        utils.create_log(compare_logs_serializer.errors)

def compare_and_liveness(image_url_1, image_url_2):
    start_time = time.time()

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            compress_future_1 = executor.submit(image_processing.compress_image, image_url_1)
            compress_future_2 = executor.submit(image_processing.compress_image, image_url_2)
            
            concurrent.futures.wait([compress_future_1, compress_future_2])
            
            compressed_image_1 = compress_future_1.result()
            compressed_image_2 = compress_future_2.result()

        if compressed_image_1["status"] != 200 or compressed_image_2["status"] != 200:
            if "filepath" in compressed_image_1 and os.path.exists(compressed_image_1["filepath"]):
                os.remove(compressed_image_1["filepath"])

            if "filepath" in compressed_image_2 and os.path.exists(compressed_image_2["filepath"]):
                os.remove(compressed_image_2["filepath"])

            return { "status": 500, "data": {}, "message": "Gagal melakukan kompresi gambar" }

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            liveness_future_1 = executor.submit(check_liveness, compressed_image_1, True)
            liveness_future_2 = executor.submit(check_liveness, compressed_image_2, True)
            compare_future = executor.submit(compare, compressed_image_1, compressed_image_2, True)
            
            concurrent.futures.wait([liveness_future_1, liveness_future_2, compare_future])
            
            liveness_result_1 = liveness_future_1.result()
            liveness_result_2 = liveness_future_2.result()
            compare_result = compare_future.result()

            if liveness_result_1["status"] != 200:
                raise Exception("Terdapat error saat mengecek liveness gambar 1")
            
            if liveness_result_2["status"] != 200:
                raise Exception("Terdapat error saat mengecek liveness gambar 2")
            
            if compare_result["status"] != 200:
                raise Exception("Terdapat error saat melakukan face compare")

            exec_time = round(time.time() - start_time, 2)

            executor.submit(image_processing.upload_image, compressed_image_1["filename"], compressed_image_1["filepath"])
            time.sleep(3)
            executor.submit(image_processing.upload_image, compressed_image_2["filename"], compressed_image_2["filepath"])

        response_data = {
            "filename_1"       : compressed_image_1["filename"],
            "filename_2"       : compressed_image_2["filename"],
            "liveness_image_1" : liveness_result_1["data"]["result"],
            "liveness_image_2" : liveness_result_2["data"]["result"],
            "face_distance"    : compare_result["data"]["face_distance"],
            "tolerance"        : compare_result["data"]["tolerance"],
            "result"           : compare_result["data"]["result"],
            "exec_time"        : "{} second".format(exec_time)
        }

        return { "status": 200, "data": response_data, "message": "" }

    except Exception as e:
        if compressed_image_1 is not None and "filepath" in compressed_image_1 and os.path.exists(compressed_image_1["filepath"]):
            os.remove(compressed_image_1["filepath"])

        if compressed_image_2 is not None and "filepath" in compressed_image_2 and os.path.exists(compressed_image_2["filepath"]):
            os.remove(compressed_image_2["filepath"])

        utils.create_log(traceback.format_exc())
        return { "status": 500, "data": {}, "message": str(e) }