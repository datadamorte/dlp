@echo off
echo Creating virtual environment...
python -m venv venv
echo Activating virtual environment...
call venv\Scripts\activate.bat
echo Installing requirements...
pip install -r requirements.txt
echo Setup complete! To run the application:
echo 1. Activate venv: venv\Scripts\activate.bat
echo 2. Run: python yt_dlp_gui.py
pause
