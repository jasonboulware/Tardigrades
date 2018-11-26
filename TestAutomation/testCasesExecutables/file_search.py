import os
import sys
sys.path.append('/home/williamsjd2/')

def files(path):  
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            yield file

