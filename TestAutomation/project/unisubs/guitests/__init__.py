import sys, os
sys.path.insert(0, '~/unisubs')
from unisubs import optionalapps

__path__.extend(os.path.join(p, 'guitests')
                for p in optionalapps.get_repository_paths())

