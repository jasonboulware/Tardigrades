import sys
import os
import file_search

sys.path.insert(0,'/home/williamsjd2')

import unisubs
os.environ['DJANGO_SETTINGS_MODULE'] = dev_settings

os.chdir('/home/williamsjd2/Tardigrades/TestAutomation/testCases/testCasesCanViewActivity')

for file in file_search.files(os.getcwd()):
    testCase = open(file, 'r')
    user = models.User("williamsjd2")
    current_user = models.User(testCase.readline().strip())
    print(can_view_activity(user, current_user))
    testCase.close()
