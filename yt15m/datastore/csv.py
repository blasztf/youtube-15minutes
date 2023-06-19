import csv
from io import TextIOWrapper
import os
import shutil
from yt15m.iface.datastore import Datastore
from yt15m.util.helper import rts, rtsg

class CsvDatastore(Datastore):
    
    def __init__(self, store, branch) -> None:
        super().__init__(store + "_csv", branch + ".csv")
        
        self.__clates = []

    def open(self) -> 'CsvDatastoreContext':
        filename = os.path.join(self.store, self.branch)

        return CsvDatastoreContext(filename)

    def close(self, context: 'CsvDatastoreContext'):
        context.close()

    def create_late(self, **kwargs):
        self.__clates.append(kwargs)

    def create_commit(self):
        if len(self.__clates) > 0:
            context = self.open()
            headers = list(self.__clates[0].keys())
            result = False
            
            try:
                reader = csv.DictReader(context.reader, fieldnames=headers, delimiter=';')
                writer = csv.DictWriter(context.writer, fieldnames=headers, delimiter=';')

                writer.writeheader()

                #if any(reader):
                # skip header
                next(reader, None)
                
                for row in reader:
                    writer.writerow(row)

                for item in self.__clates:
                    writer.writerow(item)
                
                result = True

            finally:
                self.close(context)
                self.__clates.clear()
                return result

    def create(self, **kwargs):
        context = self.open()
        headers = list(kwargs.keys())
        result = False
        
        try:
            reader = csv.DictReader(context.reader, fieldnames=headers, delimiter=';')
            writer = csv.DictWriter(context.writer, fieldnames=headers, delimiter=';')

            writer.writeheader()

            #if any(reader):
            # skip header
            next(reader, None)
            
            for row in reader:
                writer.writerow(row)
            
            writer.writerow({ key: rts(value) for key, value in kwargs.items() })
            result = True

        finally:
            self.close(context)
            return result

    def read(self, id, field_id, **kwargs):
        context = self.open()
        headers = [field_id, *list(kwargs.keys())]
        
        data = None
        try:
            reader = csv.DictReader(context.reader, fieldnames=headers, delimiter=';')

            next(reader, None)

            for row in reader:
                if row[field_id] == id:
                    data = { key: rtsg(value) for key, value in row.items() }
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

            next(reader, None)

            for row in reader:
                all_data.append({ key: rtsg(value) for key, value in row.items() })

        finally:
            self.close(context)

        return all_data

    def update(self, id, field_id, **kwargs):
        context = self.open()
        headers = [field_id, *list(kwargs.keys())]
        result = False
        
        try:
            reader = csv.DictReader(context.reader, fieldnames=headers, delimiter=';')
            writer = csv.DictWriter(context.writer, fieldnames=headers, delimiter=';')

            writer.writeheader()

            #if any(reader):
            # skip header
            next(reader, None)

            for row in reader:
                if row[field_id] == id:
                    row = { key: rts(value) for key, value in kwargs.items() }
                    row[field_id] = id
                writer.writerow(row)
            
            result = True
        finally:
            self.close(context)

        return result

    def delete(self, id, field_id, **kwargs):
        context = self.open()
        headers = [field_id, *list(kwargs.keys())]
        result = False
        
        try:
            reader = csv.DictReader(context.reader, fieldnames=headers, delimiter=';')
            writer = csv.DictWriter(context.writer, fieldnames=headers, delimiter=';')

            writer.writeheader()

            #if any(reader):
            # skip header
            next(reader, None)

            for row in reader:
                if row[field_id] == id:
                    continue
                else:
                    writer.writerow(row)
            
            result = True
        finally:
            self.close(context)

        return result

class CsvDatastoreContext:

    def __init__(self, path) -> None:
        self.__reader_path = path
        self.__writer_path = path + ".tmp"
        self.__reader = None
        self.__writer = None

        self.open()

    @property
    def reader(self):
        if not self.__reader:
            self.__reader = open(self.__reader_path, 'r', newline='')
        return self.__reader

    @property
    def writer(self):
        if not self.__writer:
            self.__writer = open(self.__writer_path, 'w', newline='')
        return self.__writer

    def open(self):
        store = os.path.dirname(self.__reader_path)
        os.makedirs(store, exist_ok=True)
        
        if not os.path.exists(self.__reader_path):
            with open(self.__reader_path, 'w'):
                pass

    def close(self):
        self.__reader.close() if self.__reader else None
        
        if self.__writer:
            self.__writer.close() 
            shutil.move(self.__writer_path, self.__reader_path)
