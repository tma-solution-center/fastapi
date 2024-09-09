import csv
from io import StringIO, BytesIO

class FileUtils:
    def __init__(self, file_name: str):
        self.file_name = file_name


    def csv_parser(self, headers, datas):
        byte_array_output_stream = BytesIO()
        try:
            buffer = StringIO()
            writer = csv.writer(buffer)

            # Ghi các tiêu đề vào CSV
            writer.writerow(headers)

            # Ghi các dữ liệu vào CSV
            for record in datas:
                writer.writerow(record)

            # Ghi nội dung từ buffer vào byte array output stream
            byte_array_output_stream.write(buffer.getvalue().encode('utf-8'))

            # Đặt con trỏ về đầu stream để đọc lại khi cần thiết
            byte_array_output_stream.seek(0)

            return byte_array_output_stream
        except Exception as e:
            raise Exception("Failed to generate CSV file.") from e

    @staticmethod
    def map_string_to_list_map(csv_data: str):
        try:
            buffer = StringIO(csv_data)
            csv_reader = csv.DictReader(buffer)
            map_data = []

            for row in csv_reader:
                map_data.append(dict(row))

            return map_data
        except Exception as e:
            return []

    @staticmethod
    def get_file_extension(file_name: str) -> str:
        if file_name and '.' in file_name:
            return file_name.rsplit('.', 1)[-1]
        return ''
