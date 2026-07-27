@echo off
echo Dang tien hanh dong goi GinContent Post thanh ban Portable (.exe)...
pyinstaller --noconfirm --onefile --windowed --add-data "icon.ico;." --add-data "logo.png;." --name "GinContent Post" --icon "icon.ico" main.py
echo ========================================================
echo Hoan tat dong goi! Dang tao file cai dat (Setup.exe)...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
echo ========================================================
echo Hoan tat! File chay nam trong thu muc: installer_output\
pause
