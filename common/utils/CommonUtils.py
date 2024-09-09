import io
from datetime import datetime

import unicodedata
import re

from starlette.responses import JSONResponse

from DATA_MODEL.model import ResponseJson


class CommonUtils:
    @staticmethod
    def convert_title_case_to_underscored_string(string: str) -> str:
        return string.strip().lower().replace(' ', '_')

    @staticmethod
    def convert_string_to_binary_io(string: str):
        # Convert the string to bytes
        byte_data = string.encode('utf-8')

        # Create a BinaryIO object from the bytes
        binary_io = io.BytesIO(byte_data)

        return binary_io

    @staticmethod
    def handle_response(data, status, message, status_code):
        # Create the response content
        response_content = ResponseJson(
            data=data,
            status=status,
            message=message
        )
        # Return the response
        return JSONResponse(content=response_content.model_dump(), status_code=status_code)

    @staticmethod
    def convert_value_in_dict_to_str(data: dict, date_formatted: str):
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.strftime(date_formatted)
            elif value:
                data[key] = str(value)
            else:
                data[key] = ""
        return data
