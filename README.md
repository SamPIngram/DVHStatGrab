# DVHStatGrab
Package for grabbing DVH statistics with little safeguarding in the case of over-anonymisation.

### Assumptions
- This package assumes that the users are able to match the correct structure and dose files themselves. There are no checks via the plan file that these are related. This does make it a viable solution in cases where the plan file is not available.

### TODOs
- Isolate DVH code and remove requirements that aren't needed (e.g. matplotlib).
- Add functionality for *simple* dose summation (i.e. assumes single structure file and multiple dose files with the same co-ordinate space.)
- Add popup for password if zip files are password locked

### For Pyinstaller:
Note on windows PyInstaller being called in this way is case-senstive
python -m PyInstaller app.py --name DVHStatGrab --collect-submodules=pydicom --add-data=venv\\Lib\\site-packages\\matplotlib.libs\\.load-order-matplotlib-3.7.1 --onefile

Need matplotlib version < 3.7 (i.e. 3.6) for pyinstaller currently
Also need to update dicompylercore's dvhcalc.py to not use np.bool (which is depreciated) and just use bool.

The created .exe needs to be run with the configs/ folder at the same level. 
