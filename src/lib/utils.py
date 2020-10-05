import csv
import uuid


def read_csv_without_header(path):
    file = open(path, 'r')
    try:
        file.readline()
        reader = csv.reader(file, delimiter=',')
        data = list(reader)
        return data
    finally:
        file.close()


def generate_uuid():
    return uuid.uuid4()
