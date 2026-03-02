import sys, importlib
sys.path.append(r"C:\Users\rahul\Downloads\NPDC_PROJECT")
try:
    importlib.import_module('data_submission.views')
    print('import success')
except Exception as e:
    print('import error', e)
