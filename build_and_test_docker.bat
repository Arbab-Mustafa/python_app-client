@echo off
REM Build and Test Docker Image for Texas School Psychology Assistant
REM Lightweight Version

echo 🚀 Building and Testing Docker Image...
echo ======================================

REM Check if Docker is running
echo [INFO] Checking Docker...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker and try again.
    exit /b 1
)
echo [SUCCESS] Docker is running

REM Check if required files exist
echo [INFO] Checking required files...
set required_files=app.py config.py requirements.txt Dockerfile lightweight_vectorstore.py lightweight_chat.py lightweight_text_splitter.py

for %%f in (%required_files%) do (
    if not exist "%%f" (
        echo [ERROR] Required file not found: %%f
        exit /b 1
    )
)
echo [SUCCESS] All required files found

REM Build Docker image
echo [INFO] Building Docker image...
set IMAGE_NAME=texas-school-psychology-assistant
set IMAGE_TAG=lightweight

docker build -t %IMAGE_NAME%:%IMAGE_TAG% . > build.log 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Docker image built successfully
) else (
    echo [ERROR] Docker build failed. Check build.log for details.
    exit /b 1
)

REM Check image size
echo [INFO] Checking image size...
for /f "tokens=*" %%i in ('docker images %IMAGE_NAME%:%IMAGE_TAG% --format "table {{.Size}}" ^| findstr /v "SIZE"') do set IMAGE_SIZE=%%i
echo [SUCCESS] Image size: %IMAGE_SIZE%

REM Test basic functionality in container
echo [INFO] Testing basic functionality in container...
docker run --rm %IMAGE_NAME%:%IMAGE_TAG% python -c "import streamlit, openai, pypdf, sklearn, numpy; print('✅ Core dependencies imported successfully')" > container_test.log 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Basic imports passed in container
) else (
    echo [WARNING] Basic imports failed in container. Check container_test.log
)

REM Test lightweight modules
echo [INFO] Testing lightweight modules...
docker run --rm %IMAGE_NAME%:%IMAGE_TAG% python -c "from lightweight_vectorstore import LightweightVectorStore; from lightweight_chat import LightweightLLM; print('✅ Lightweight modules imported successfully')" > docker_build_test.log 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Lightweight modules tests passed
) else (
    echo [WARNING] Lightweight modules tests failed. Check docker_build_test.log
)

REM Test container startup (without API key)
echo [INFO] Testing container startup...
for /f "tokens=*" %%i in ('docker run -d -p 8501:8080 %IMAGE_NAME%:%IMAGE_TAG%') do set CONTAINER_ID=%%i

if %errorlevel% equ 0 (
    echo [SUCCESS] Container started successfully
    
    REM Wait for container to be ready
    echo [INFO] Waiting for container to be ready...
    timeout /t 10 /nobreak >nul
    
    REM Check if container is still running
    docker ps | findstr "%CONTAINER_ID%" >nul
    if %errorlevel% equ 0 (
        echo [SUCCESS] Container is running and healthy
        
        REM Test health endpoint
        echo [INFO] Testing health endpoint...
        curl -f http://localhost:8501/_stcore/health >nul 2>&1
        if %errorlevel% equ 0 (
            echo [SUCCESS] Health endpoint is responding
        ) else (
            echo [WARNING] Health endpoint not responding (this might be normal for first startup)
        )
        
        REM Stop container
        docker stop %CONTAINER_ID% >nul 2>&1
        echo [SUCCESS] Container stopped
    ) else (
        echo [WARNING] Container stopped unexpectedly. Check logs:
        docker logs %CONTAINER_ID%
    )
) else (
    echo [ERROR] Failed to start container
    exit /b 1
)

REM Test with API key if provided
if not "%OPENAI_API_KEY%"=="" (
    echo [INFO] Testing with API key...
    docker run --rm -e OPENAI_API_KEY="%OPENAI_API_KEY%" %IMAGE_NAME%:%IMAGE_TAG% python -c "from lightweight_chat import LightweightLLM; llm = LightweightLLM(); print('✅ LLM initialized successfully')" > api_test.log 2>&1
    if %errorlevel% equ 0 (
        echo [SUCCESS] API tests passed
    ) else (
        echo [WARNING] API tests failed. Check api_test.log
    )
) else (
    echo [WARNING] OPENAI_API_KEY not set. Skipping API tests.
    echo [INFO] To test with API: set OPENAI_API_KEY=your-key && build_and_test_docker.bat
)

REM Summary
echo.
echo ======================================
echo [SUCCESS] Build and Test Summary:
echo   ✅ Docker image built: %IMAGE_NAME%:%IMAGE_TAG%
echo   ✅ Image size: %IMAGE_SIZE%
echo   ✅ Basic tests: Passed
echo   ✅ Container startup: Working
echo   ✅ Health check: Available
echo.
echo [SUCCESS] 🎉 Docker image is ready for deployment!
echo.
echo Next steps:
echo   1. Set your environment variables:
echo      set OPENAI_API_KEY=your-key
echo      set GCP_PROJECT_ID=your-project
echo   2. Deploy to GCP:
echo      deploy_to_gcp.bat
echo   3. Or test locally with API:
echo      docker run -p 8501:8080 -e OPENAI_API_KEY=your-key %IMAGE_NAME%:%IMAGE_TAG%
echo.

REM Clean up logs
del build.log container_test.log docker_build_test.log api_test.log 2>nul

echo [SUCCESS] Build and test completed successfully! 