import os


class Dupfilter:
    def __init__(self, path='./', name='dupfilter.seen'):
        self.spath = os.path.join(path, name)
        self.file = None
        self.fingerprints = set()
        if path:
            self.file = open(self.spath, 'a+', encoding='utf-8')
            self.file.seek(0)
            self.fingerprints.update(x.rstrip() for x in self.file)

    def is_crawled(self, data):
        fp = data
        if fp in self.fingerprints:
            return True
        self.fingerprints.add(fp)
        if self.file:
            self.file.write(fp + '\n')
            self.file.flush()
        return False

    def close(self):
        if self.file:
            self.file.close()
