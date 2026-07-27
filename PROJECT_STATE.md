# Trạng Thái Dự Án: GinContent Post & License Manager

Tài liệu này lưu trữ toàn bộ kiến trúc và các tính năng đã được xây dựng để làm "bộ nhớ" cho các phiên làm việc (cuộc trò chuyện) tiếp theo. Bất cứ khi nào bạn bắt đầu một chat mới, AI có thể đọc file này để ngay lập tức hiểu toàn bộ bối cảnh.

## 1. Cấu Trúc Tổng Quan
Dự án bao gồm 2 phần mềm Python chạy độc lập, giao tiếp với nhau thông qua cơ sở dữ liệu đám mây **Supabase** (URL: `https://ahixqnsnpdvtrakqaynl.supabase.co`).

- **GinContent Post**: Phần mềm dành cho khách hàng. Chức năng chính là lấy file `.docx` và hình ảnh từ Google Drive, tự động đăng lên WordPress dưới dạng bản nháp (Draft). Giao diện được thiết kế theo phong cách Glassmorphism Dark Theme.
- **GinContent License Manager**: Phần mềm dành cho Admin (bạn). Dùng để quản lý vòng đời của các mã kích hoạt bản quyền (Tạo mới, Khóa, Reset thiết bị).

## 2. Tính Năng & Logic Cốt Lõi Đã Hoàn Thiện

### A. Hệ Thống Bản Quyền (Licensing)
- **Cơ chế 1 Thiết Bị (HWID)**: Phần mềm tự động lấy mã phần cứng (UUID + MAC) của máy tính. Mỗi License Key chỉ được gắn cứng vào 1 máy tính duy nhất. File `license.lic` lưu dưới máy khách được mã hóa XOR bằng chính HWID để chống copy file sang máy khác.
- **Lưu Vết Khách Hàng**: Tự động lưu lại tên thiết bị (`device_name`), ngày kích hoạt đầu tiên (`activated_at`) và thời gian truy cập gần nhất (`last_seen`) để Admin dễ quản lý.
- **Logic Gia Hạn 30 Ngày**: 
  - Khi tạo Key mới từ phần mềm Admin, Key ở trạng thái `unused` (Chưa kích hoạt).
  - Khi khách hàng nhập Key lần đầu tiên, hệ thống đổi trạng thái thành `active`, thiết lập hạn sử dụng là **30 ngày kể từ thời điểm đó** và lưu vào Supabase.
- **Tường Lửa Ứng Dụng (License Wall)**: Trong file `main.py`, ngay khi phần mềm khởi động, hàm `check_offline_license()` được gọi. Nếu không có file bản quyền hợp lệ, toàn bộ giao diện bị ẩn đi và thay bằng khung yêu cầu nhập License Key.

### B. GinContent Post (Client)
- **Tối ưu URL (Slug) chuẩn SEO**: Bài đăng lên WordPress sẽ tự động lấy tên gốc của file `.docx` làm đường dẫn URL. (VD: `bai-viet-so-1.docx` -> URL: `.../bai-viet-so-1`).
- **Hỗ trợ đa nền tảng (Windows & MacOS)**:
  - Bản Windows: Được đóng gói thành `.exe` Portable bằng PyInstaller. Đã fix lỗi văng app khi chạy chế độ `--windowed` bằng cách ghi đè `sys.stdout`.
  - Bản MacOS: Được tự động build ra file `.app` thông qua hệ thống **GitHub Actions** mỗi khi bạn dùng lệnh `git push`. (Do Windows không thể build chéo sang Mac). Toàn bộ logic bản quyền vẫn hoạt động hoàn hảo trên Mac.

### C. GinContent License Manager (Admin)
- Tạo mã ngẫu nhiên định dạng: `GINPOST-XXXX-XXXX` (1 click là tạo xong).
- Bảng quản lý (Table) liệt kê các mã, ngày hết hạn, số thiết bị đang kết nối.
- Nút **Reset** (Xóa HWID) để khách đăng nhập máy mới.
- Nút **Khóa / Mở Khóa** để đình chỉ bản quyền khách hàng.

## 3. Lệnh Cần Nhớ (Dành cho Phiên Chat Sau)
- **Lệnh build bản Windows Portable (Client)**: 
  `cd C:\Users\KEY\Gravity2\gincontent-post`
  `pyinstaller --noconfirm --onedir --windowed --name "GinContent Post" main.py`
- **Lệnh build bản Windows Portable (Admin)**: 
  `cd C:\Users\KEY\Gravity2\gincontent-license-manager`
  `pyinstaller --noconfirm --onedir --windowed --name "GinContent License Manager" main.py`
- **Lệnh cập nhật lên GitHub để build bản Mac**:
  `git add .`
  `git commit -m "update"`
  `git push -u origin main` (Sau đó vào tab Actions trên GitHub để tải `.app`).
