
from UserDict import DictMixin
from ConfigParser import ConfigParser, NoOptionError
import datetime
import os
import subprocess

class ConfigMap(DictMixin):

    def __init__(self, parser):
        self.parser = parser
        self.sects = parser.sections()

    def __iter__(self):
        for sname in self.sects:
            yield sname
            
    def __getitem__(self, idx):
        return OptionMap(self.parser, idx)

    def __setitem__(self, idx, val):
        for item in val.items():
            self.parser.set(*(idx,) + item)

    def __delitem__(self, idx):
        self.parser.remove_section(idx)

    def keys(self):
        return self.parser.sections()

    def write(self, fn):
        self.parser.write(fn)

    @classmethod
    def load(cls, fname):
        parser = ConfigParser()
        parser.read(fname)
        return cls(parser)


class OptionMap(DictMixin):
    def __init__(self, parser, section):
        self.parser = parser
        self.section = section
        
    def __getitem__(self, idx):
        try:
            return self.parser.get(self.section, idx)
        except NoOptionError, e:
            raise KeyError(e)

    def __setitem__(self, name, val):
        self.parser.set(self.section, name, val)

    def __delitem__(self, name):
        self.parser.remove_option(self.section, name)

    def keys(self):
        return self.parser.options(self.section)


def get_version(version=None):
    "Returns a PEP 386-compliant version number from VERSION."
    if version is None:
        from geonode import __version__ as version
    else:
        assert len(version) == 5
        assert version[3] in ('alpha', 'beta', 'rc', 'final')

    # Now build the two parts of the version number:
    # main = X.Y[.Z]
    # sub = .devN - for pre-alpha releases
    #     | {a|b|c}N - for alpha, beta and rc releases

    parts = 2 if version[2] == 0 else 3
    main = '.'.join(str(x) for x in version[:parts])

    sub = ''
    if version[3] == 'alpha' and version[4] == 0:
        git_changeset = get_git_changeset()
        if git_changeset:
            sub = '.dev%s' % git_changeset

    elif version[3] != 'final':
        mapping = {'alpha': 'a', 'beta': 'b', 'rc': 'c'}
        sub = mapping[version[3]] + str(version[4])

    return main + sub


def get_git_changeset():
    """Returns a numeric identifier of the latest git changeset.

    The result is the UTC timestamp of the changeset in YYYYMMDDHHMMSS format.
    This value isn't guaranteed to be unique, but collisions are very unlikely,
    so it's sufficient for generating the development version numbers.
    """
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    git_show = subprocess.Popen('git show --pretty=format:%ct --quiet HEAD',
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=True, cwd=repo_dir, universal_newlines=True)
    timestamp = git_show.communicate()[0].partition('\n')[0]
    try:
        timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))
    except ValueError:
        return None
    return timestamp.strftime('%Y%m%d%H%M%S')

class WorldmapDatabaseRouter(object):
    """A router to control all database operations on models in
    the myapp application"""

    def db_for_read(self, model, **hints):
        "Point all operations on myapp models to 'other'"
        if model._meta.app_label == 'gazetteer':
            return 'wmdata'
        return None

    def db_for_write(self, model, **hints):
        "Point all operations on myapp models to 'other'"
        if model._meta.app_label == 'gazetteer':
            return 'wmdata'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        "Allow any relation if a model in myapp is involved"
        if obj1._meta.app_label == 'gazetteer' or obj2._meta.app_label == 'gazetteer':
            return True
        return None

    def allow_syncdb(self, db, model):
        "Make sure the myapp app only appears on the 'other' db"
        if db == 'wmdata':
            return model._meta.app_label == 'gazetteer'
        elif model._meta.app_label == 'gazetteer':
            return False
        return None
