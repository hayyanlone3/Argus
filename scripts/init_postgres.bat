@echo off

REM Try to find psql in common D: locations
set "PSQL_PATH=D:\PostgreSQL\16\bin\psql.exe"

if not exist "%PSQL_PATH%" (
    set "PSQL_PATH=D:\PostgreSQL\15\bin\psql.exe"
)

if not exist "%PSQL_PATH%" (
    set "PSQL_PATH=D:\PostgreSQL\14\bin\psql.exe"
)

REM Check if psql exists
if not exist "%PSQL_PATH%" (
    echo   PostgreSQL not found on D: drive
    echo.
    echo Expected location: D:\PostgreSQL\XX\bin\psql.exe
    echo.
    echo Please verify:
    echo 1. PostgreSQL is installed on D: drive
    echo 2. Check which version is installed (14, 15, 16, etc.)
    echo 3. Update the script with correct version number
    echo.
    pause
    exit /b 1
)

echo   PostgreSQL found at: %PSQL_PATH%
echo.

REM Get postgres password (default is often blank or 'postgres')
set /p POSTGRES_PASSWORD="Enter PostgreSQL superuser (postgres) password: "

if "!POSTGRES_PASSWORD!"=="" (
    echo Using no password (if set during install)
    set "PSQL_CMD=%PSQL_PATH% -U postgres -h localhost"
) else (
    set "PSQL_CMD=%PSQL_PATH% -U postgres -h localhost"
)

REM Create ARGUS user and database
echo.
echo 🗄️  Creating ARGUS database and user...
echo    User: argus
echo    Password: password123
echo    Database: argus_db
echo.

REM Test connection first
%PSQL_CMD% -c "SELECT 1;" >nul 2>&1
if %errorlevel% neq 0 (
    echo   Cannot connect to PostgreSQL
    echo.
    echo Possible reasons:
    echo 1. PostgreSQL service is not running
    echo 2. Superuser password is incorrect
    echo 3. PostgreSQL is not on D: drive
    echo.
    echo To start PostgreSQL service:
    echo   Press Windows + R
    echo   Type: services.msc
    echo   Find: PostgreSQL
    echo   Right-click: Start
    echo.
    pause
    exit /b 1
)

REM Create user
echo Creating user 'argus'...
%PSQL_CMD% -c "DROP USER IF EXISTS argus;" >nul 2>&1
%PSQL_CMD% -c "CREATE USER argus WITH PASSWORD 'password123';" >nul 2>&1

if %errorlevel% neq 0 (
    echo    User creation issue (may already exist)
)

REM Create database
echo Creating database 'argus_db'...
%PSQL_CMD% -c "DROP DATABASE IF EXISTS argus_db;" >nul 2>&1
%PSQL_CMD% -c "CREATE DATABASE argus_db OWNER argus;" >nul 2>&1

if %errorlevel% neq 0 (
    echo   Database creation failed
    pause
    exit /b 1
)

REM Grant privileges
echo Granting privileges...
%PSQL_CMD% -c "GRANT ALL PRIVILEGES ON DATABASE argus_db TO argus;" >nul 2>&1

echo.
echo ════════════════════════════════════════════════════════════════════════════
echo   PostgreSQL SETUP COMPLETE
echo ════════════════════════════════════════════════════════════════════════════
echo.
echo Connection Details:
echo   Host:     localhost
echo   Port:     5432
echo   Username: argus
echo   Password: password123
echo   Database: argus_db
echo   Location: D:\PostgreSQL\XX (your drive)
echo.
echo Update your .env file with:
echo   DATABASE_URL=postgresql://argus:8888@localhost:5432/argus_db
echo.
echo Next step:
echo   python scripts/init_db.py
echo.
pause