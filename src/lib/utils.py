import csv
import uuid


def read_csv(path):
    file = open(path, 'r')
    try:
        reader = csv.reader(file, delimiter=',')
        data = list(reader)
        return data
    finally:
        file.close()


def get_uuid():
    return uuid.uuid4()
