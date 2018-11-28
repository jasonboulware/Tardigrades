import sys, os
sys.path.insert(0, '../..')
import unisubs.optionalapps

__path__.extend(os.path.join(p, 'guitests')
                for p in unisubs.optionalapps.get_repository_paths())

