#!/bin/bash

# Hướng dẫn: Mở Terminal trên Macbook, cd vào thư mục chứa code này và chạy lệnh: sh build_mac.sh

echo "🚀 Bắt đầu cài đặt thư viện..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

echo "📦 Đang tiến hành đóng gói (Build) cho macOS..."
pyinstaller --noconfirm --onefile --windowed --name "GinContent Post" main.py

echo "✅ Hoàn tất! Ứng dụng Mac của bạn nằm ở dist/GinContent Post.app"
