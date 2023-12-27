import ntpath
import posixpath
import sys
import os


class PathUtils:
    @classmethod
    def isabs(cls, path: str) -> bool:
        if sys.platform == 'win32':
            return ntpath.isabs(path)
        else:
            return posixpath.isabs(path)

    @classmethod
    def get_dir(cls, abs_path: str) -> str:
        return os.path.dirname(abs_path)

    @classmethod
    def get_basename(cls, path: str) -> str:
        return os.path.basename(path)
    
    @classmethod
    def join(cls, *paths: str) -> str:
        return os.path.join(*paths)

