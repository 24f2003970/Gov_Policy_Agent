from app.config import Settings
from app.embedding import prepare, SPEC

if __name__ == '__main__':
    prepare(Settings())
    print('Prepared offline CPU embedding model:', SPEC)
