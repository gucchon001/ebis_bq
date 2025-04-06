@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ===== Test Execution Tool =====
echo.

:: Python が利用可能か確認
python --version > nul 2>&1
if errorlevel 1 (
    echo Error: Python not found.
    echo Please make sure Python is installed.
    goto END
)

:: 仮想環境の存在確認
if not exist "venv" (
    echo Virtual environment not found. Creating new one...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        goto END
    )
    echo Virtual environment created.
)

:: 仮想環境をアクティベート
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment.
    goto END
)

echo Virtual environment activated.

:: 必要なパッケージがインストールされているか確認
python -c "import pytest" > nul 2>&1
if errorlevel 1 (
    echo pytest is not installed. Installing...
    pip install pytest pytest-html
    if errorlevel 1 (
        echo Failed to install pytest.
        goto DEACTIVATE
    )
)

:: 結果ディレクトリの作成
if not exist "tests\results" (
    mkdir "tests\results"
)

:MENU
echo.
echo Please select execution mode:
echo 1: Run all tests
echo 2: Run all tests including skipped tests
echo 3: Run individual test
echo 4: Show test result summary
echo 5: Export test report
echo 6: Exit
echo.

set /p mode="Selection (1-6): "

if "%mode%"=="1" goto RUN_ALL
if "%mode%"=="2" goto RUN_ALL_INCLUDING_SKIPPED
if "%mode%"=="3" goto SELECT_TEST
if "%mode%"=="4" goto SHOW_SUMMARY
if "%mode%"=="5" goto EXPORT_REPORT
if "%mode%"=="6" goto DEACTIVATE

echo Invalid selection. Please try again.
goto MENU

:: すべてのテストを実行 - src/utils/test_runner.pyを使用
:RUN_ALL
echo.
echo Running all tests...
echo.

:: test_runner.pyを使用してテストを実行
python -m src.utils.test_runner tests -v --report

echo.
echo All tests completed. Some tests might have been skipped due to errors.
echo Test results are stored in the tests\results folder.
echo.

echo Show test result summary? (Y/N)
set /p show_summary="Selection: "
if /i "%show_summary%"=="Y" goto SHOW_SUMMARY
goto MENU

:: スキップテストも含めてすべてのテストを実行
:RUN_ALL_INCLUDING_SKIPPED
echo.
echo Running all tests ignoring skip marks...
echo.

:: test_runner.pyを使用してテストを実行 (スキップマークを無視する)
python -m src.utils.test_runner tests -v --report --no-skip --run-xfail

echo.
echo All tests (including skipped tests) completed.
echo Test results are stored in the tests\results folder.
echo.

echo Show test result summary? (Y/N)
set /p show_summary="Selection: "
if /i "%show_summary%"=="Y" goto SHOW_SUMMARY
goto MENU

:: 個別のテストを選択して実行
:SELECT_TEST
echo.
echo Select a test to run:

set i=1
for %%f in (tests\test_*.py) do (
    echo !i!: %%~nf
    set "file[!i!]=%%f"
    set /a i+=1
)

echo !i!: Back
echo.

set /p test_choice="Select test number (1-!i!): "

if %test_choice% EQU !i! goto MENU

if not defined file[%test_choice%] (
    echo Invalid selection. Please try again.
    goto SELECT_TEST
)

set selected_test=!file[%test_choice%]!
echo.
echo Running !selected_test!...
echo.

:: test_runner.pyを使用して特定のテストを実行
python -m src.utils.test_runner "!selected_test!" -v --report

echo.
echo Test completed. Some tests might have been skipped due to errors.
echo Test results are stored in the tests\results folder.
echo.

echo Show test result summary? (Y/N)
set /p show_summary="Selection: "
if /i "%show_summary%"=="Y" goto SHOW_SUMMARY
goto MENU

:: テスト結果サマリーを表示 - src/utils/test_summary.pyを使用
:SHOW_SUMMARY
echo.
echo Generating test result summary...
echo.

:: サマリースクリプトの実行
python -m src.utils.test_summary

echo.
echo Press any key to return to the menu...
pause > nul
goto MENU

:: テスト結果レポートをファイル出力 - src/utils/test_summary.pyを使用
:EXPORT_REPORT
echo.
echo Generating test result report...
echo.

echo Select output format:
echo 1: Text format (TXT)
echo 2: JSON format
echo 3: Both
echo 4: Back
echo.

set /p format_choice="Selection (1-4): "

if "%format_choice%"=="1" (
    python -c "from src.utils.test_summary import TestSummaryGenerator; generator = TestSummaryGenerator(); path = generator.export_summary(format='txt'); print('Test results saved to ' + str(path))"
    goto MENU
) else if "%format_choice%"=="2" (
    python -c "from src.utils.test_summary import TestSummaryGenerator; generator = TestSummaryGenerator(); path = generator.export_summary(format='json'); print('Test results saved to ' + str(path))"
    goto MENU
) else if "%format_choice%"=="3" (
    python -c "from src.utils.test_summary import TestSummaryGenerator; generator = TestSummaryGenerator(); path1 = generator.export_summary(format='txt'); path2 = generator.export_summary(format='json'); print('Test results saved to ' + str(path1) + ' and ' + str(path2))"
    goto MENU
) else if "%format_choice%"=="4" (
    goto MENU
) else (
    echo Invalid selection. Please try again.
    goto EXPORT_REPORT
)

:DEACTIVATE
:: 仮想環境を非アクティベート
call venv\Scripts\deactivate.bat

:END
echo.
echo Process completed.
pause
endlocal 