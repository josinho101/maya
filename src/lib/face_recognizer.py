from . import utils
from .models.subject import Subject
import cv2


class FaceRecognizer:
    def __init__(self, model_csv_path, image_base_path):
        self.__model_csv_path = model_csv_path
        self.__image_base_path = image_base_path
        self.__subjects = []

    def train_models(self):
        model_data = utils.read_csv_without_header(self.__model_csv_path)
        for model in model_data:
            image_name = model[1]
            subject_name = model[0]

            filename = self.__image_base_path + '/' + image_name
            image = cv2.imread(filename)
            subject = Subject(subject_name, image_name)
            subject.image = image
            self.__subjects.append(subject)

        # find encodings of images
