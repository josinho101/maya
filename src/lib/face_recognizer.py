from . import utils
from .models.subject import Subject
import cv2
import face_recognition


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
            # find encoding
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            subject.image = face_recognition.face_encodings(image)[0]
            self.__subjects.append(subject)
