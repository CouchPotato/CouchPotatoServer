
from six import PY2


if PY2:
    from CodernityDB.database_super_thread_safe import SuperThreadSafeDatabase
    from CodernityDB.index import IndexException, IndexConflict, IndexNotFoundException
    from CodernityDB.database import RecordNotFound, RecordDeleted
    from CodernityDB.hash_index import HashIndex
    from CodernityDB.tree_index import MultiTreeBasedIndex, TreeBasedIndex
else:
    from CodernityDB3.database_super_thread_safe import SuperThreadSafeDatabase
    from CodernityDB3.index import IndexException, IndexConflict, IndexNotFoundException
    from CodernityDB3.database import RecordNotFound, RecordDeleted
    from CodernityDB3.hash_index import HashIndex
    from CodernityDB3.tree_index import MultiTreeBasedIndex, TreeBasedIndex

SuperThreadSafeDatabase = SuperThreadSafeDatabase
IndexException = IndexException
IndexNotFoundException = IndexNotFoundException
IndexConflict = IndexConflict
RecordNotFound = RecordNotFound
HashIndex = HashIndex
MultiTreeBasedIndex = MultiTreeBasedIndex
TreeBasedIndex = TreeBasedIndex
RecordDeleted = RecordDeleted
