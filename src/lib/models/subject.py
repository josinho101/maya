class Subject:
    def __init__(self, name, image_path):
        self.__name = name
        self.__image_path = image_path
        self.image = None

    def get_name(self):
        return self.__name

    def get_image_path(self):
        return self.__image_path
