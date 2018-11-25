import os

import optionalapps

__path__.extend(os.path.join(p, 'guitests')
                for p in optionalapps.get_repository_paths())

