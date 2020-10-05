from lib.face_recognizer import FaceRecognizer

model_csv = 'src/content/model.csv'
image_base_path = 'src/content/images'

fr = FaceRecognizer(model_csv, image_base_path)
fr.train_models()

print('model training completed')
