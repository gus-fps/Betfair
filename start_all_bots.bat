@echo off
cd /d "%~dp0"

start "BTTS"    cmd /k python ghost_bot_BTTS_v2.py
start "Draw HT" cmd /k python ghost_bot_Draw_HT.py
start "O1.5HT"  cmd /k python ghost_bot_O1.5HT.py
start "LTD"     cmd /k python ghost_bot_LTD_pre_live.py
start "U2.5 1H" cmd /k python ghost_bot_U2.5_1H_15min.py
start "BTTS No" cmd /k python ghost_bot_BTTS_No.py
start "O1.5 FT"  cmd /k python ghost_bot_O15_final.py
start "O2.5 UY"  cmd /k python ghost_bot_O2.5_UY_KR.py
