# Sử dụng image Python chính thức làm base image
FROM python:3.9-slim

# Đặt biến môi trường
ENV PYTHONUNBUFFERED=1

# Tạo và sử dụng thư mục làm việc
WORKDIR /app

# Sao chép tệp requirements.txt vào image
COPY requirements.txt .

# Cài đặt các phụ thuộc từ requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn ứng dụng vào image
COPY . .

# Lệnh khởi động Uvicorn server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
