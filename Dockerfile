# Sử dụng image Python chính thức làm base image
FROM python:3.9-slim

# Đặt biến môi trường
ENV PYTHONUNBUFFERED=1
ENV VAULT_TOKEN=hvs.ii1Ov7Y5r1nbRXdgni01tzYA
ENV VAULT_URL=http://192.168.76.120:30050/


# Tạo và sử dụng thư mục làm việc
WORKDIR /app

RUN apt-get install pkg-config python3-dev default-libmysqlclient-dev build-essential

# Sao chép tệp requirements.txt vào image
COPY requirements.txt .

# Cài đặt các phụ thuộc từ requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn ứng dụng vào image
COPY . .

# Lệnh khởi động Uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
