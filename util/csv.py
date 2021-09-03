import csv

def write(file, content):
    with open(file, "a+") as f:
        writer = csv.writer(f)
        writer.writerow(content)

def read(file):
    with open(file, "r") as f:
        return csv.reader(f)
