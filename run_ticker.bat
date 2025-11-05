@echo off
cd /d "%~dp0"
echo Iniciando TIKER_TIPE...
pip install -r requirements.txt
streamlit run app.py
pause
