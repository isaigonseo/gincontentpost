#!/bin/bash

# Hướng dẫn: Mở Terminal trên Macbook, cd vào thư mục chứa code này và chạy lệnh: sh build_mac.sh

echo "🚀 Bắt đầu cài đặt thư viện..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

echo "📦 Đang tiến hành đóng gói (Build) cho macOS..."
pyinstaller --noconfirm --windowed --add-data "logo.png:." --add-data "icon.ico:." --name "GinContent Post" main.py

echo "💿 Đang tạo file DMG cài đặt..."
hdiutil create -volname "GinContent Post" -srcfolder "dist/GinContent Post.app" -ov -format UDZO "dist/GinContent-Post.dmg"

echo "✅ Hoàn tất! File cài đặt cho Mac của bạn nằm ở dist/GinContent-Post.dmg"
