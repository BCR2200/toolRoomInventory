@echo off
:: Full path to Git Bash (adjust if necessary)
set "GITBASH=C:\Program Files\Git\bin\bash.exe"

:: Full path to the directory where setup.bash and main.py are located
set "PROJECT_DIR=C:\Users\BCR CAD 3\Desktop\toolRoomInventory"

:: Run Git Bash with the specified commands
"%GITBASH%" --login -i -c "cd '%PROJECT_DIR%' && . setup.bash && python main.py"
