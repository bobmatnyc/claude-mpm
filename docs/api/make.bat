@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
set SOURCEDIR=.
set BUILDDIR=_build
set PROJECTDIR=..\..

if "%1" == "" goto help

%SPHINXBUILD% >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Make sure you have Sphinx
	echo.installed, then set the SPHINXBUILD environment variable to point
	echo.to the full path of the 'sphinx-build' executable. Alternatively you
	echo.may add the Sphinx directory to PATH.
	echo.
	echo.If you don't have Sphinx installed, grab it from
	echo.https://www.sphinx-doc.org/
	exit /b 1
)

if "%1" == "install-deps" goto install-deps
if "%1" == "autodoc" goto autodoc
if "%1" == "html-open" goto html-open
if "%1" == "all" goto all
if "%1" == "check" goto check
if "%1" == "coverage" goto coverage

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:install-deps
pip install sphinx sphinx-rtd-theme
goto end

:autodoc
sphinx-apidoc -o . %PROJECTDIR%\src\claude_mpm --force --separate --module-first
goto end

:html-open
call %SPHINXBUILD% -M html %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
echo Opening documentation in browser...
start %BUILDDIR%\html\index.html
goto end

:all
rmdir /s /q %BUILDDIR% 2>NUL
call :autodoc
%SPHINXBUILD% -M html %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:check
%SPHINXBUILD% -W -b html %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:coverage
%SPHINXBUILD% -b coverage %SOURCEDIR% %BUILDDIR%\coverage %SPHINXOPTS% %O%
echo Coverage report generated in %BUILDDIR%\coverage\
goto end

:end
popd
