import csv
from io import TextIOWrapper
import os
import shutil
from yt15m.iface.datastore import Datastore
from yt15m.datastore.csv import CsvDatastoreContext

class CsvDatastore(Datastore):
    
    def __init__(self, store, branch) -> None:
        super().__init__(store + "_csv", branch + ".csv")

    def open(self) -> CsvDatastoreContext:
        filename = os.path.join(self.store, self.branch)
        return CsvDatastoreContext(filename)

    def close(self, context: CsvDatastoreContext):
        context.close()

    def create(self, **kwargs):
        context = self.open()
        headers = list(kwargs.keys())
        
        try:
            reader = csv.DictReader(context.reader, fieldnames=headers, delimiter=';')
            writer = csv.DictWriter(context.writer, fieldnames=headers, delimiter=';')

            writer.writeheader()

            for row in reader:
                writer.writerow(row)

            writer.writerow({ key: str(value) for key, value in kwargs.items() })

        finally:
            self.close(context)

    def read(self, id, field_id, **kwargs):
        context = self.open()
        headers = list(kwargs.keys())
        
        data = None
        try:
            reader = csv.DictReader(context.reader, fieldnames=headers, delimiter=';')

            for row in reader:
                if row[field_id] == id:
                    data = row
                    break

        finally:
            self.close(context)

        return data

    def read_all(self, **kwargs):
        context = self.open()
        headers = list(kwargs.keys())
        
        all_data = []
        try:
            reader = csv.DictReader(context.reader, fieldnames=headers, delimiter=';')

            for row in reader:
                all_data.append(row)

        finally:
            self.close(context)

        return all_data

    def update(self, id, field_id, **kwargs):
        context = self.open()
        headers = list(kwargs.keys())
        
        try:
            reader = csv.DictReader(context.reader, fieldnames=headers, delimiter=';')
            writer = csv.DictWriter(context.writer, fieldnames=headers, delimiter=';')

            writer.writeheader()

            for row in reader:
                if row[field_id] == id:
                    row = { key: str(value) for key, value in kwargs.items() }
                writer.writerow(row)

        finally:
            self.close(context)

    def delete(self, id, field_id, **kwargs):
        context = self.open()
        headers = list(kwargs.keys())
        
        try:
            reader = csv.DictReader(context.reader, fieldnames=headers, delimiter=';')
            writer = csv.DictWriter(context.writer, fieldnames=headers, delimiter=';')

            writer.writeheader()

            for row in reader:
                if row[field_id] == id:
                    continue
                writer.writerow(row)

        finally:
            self.close(context)

class CsvDatastoreContext:

    def __init__(self, path) -> None:
        self.__reader_path = path
        self.__writer_path = path + ".tmp"
        self.__reader = None
        self.__writer = None

        self.open()

    @property
    def reader(self):
        return self.__reader

    @property
    def writer(self):
        return self.__writer

    def open(self):
        store = os.path.dirname(self.__reader_path)
        os.makedirs(store, exist_ok=True)

        if not os.path.exists(self.__reader_path):
            with open(self.__reader_path, 'w'):
                pass

        self.__reader = open(self.__reader_path, 'r', newline='')
        self.__writer = open(self.__writer_path, 'w', newline='')

    def close(self):
        self.__reader.close()
        self.__writer.close()

        shutil.move(self.__writer_path, self.__reader_path)
