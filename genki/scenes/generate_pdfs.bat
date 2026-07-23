@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ===================================================
echo   日本語会話学習シート PDF結合生成スクリプト 起動
echo ===================================================
echo.

:: 1. 通常の python コマンドで試行
echo [試行 1] python コマンドで実行しています...
python generate_pdfs.py
if %errorlevel% equ 0 goto success

echo.
:: 2. py ランチャーでの実行を試行 (Windows環境で有効なケースが多いです)
echo [試行 2] py コマンドで実行しています...
py generate_pdfs.py
if %errorlevel% equ 0 goto success

:error
echo.
echo ---------------------------------------------------
echo [エラー] スクリプトの実行に失敗しました。
echo ※ライブラリ不足（playwright等）か、Pythonのパスが通っていない可能性があります。
echo ---------------------------------------------------
goto end

:success
echo.
echo ===================================================
echo [完了] すべての結合PDFが正常に生成されました。
echo ===================================================

:end
echo.
echo 画面を固定しています。エラー内容を確認したら、何かキーを押して閉じてください。
pause > nul