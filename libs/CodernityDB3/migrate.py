#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2011-2013 Codernity (http://codernity.com)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from CodernityDB3.database import Database
import shutil
import os


def migrate(source, destination):
    """
    Very basic for now
    """
    dbs = Database(source)
    dbt = Database(destination)
    dbs.open()
    dbt.create()
    dbt.close()
    for curr in os.listdir(os.path.join(dbs.path, '_indexes')):
        if curr != '00id.py':
            shutil.copyfile(os.path.join(dbs.path, '_indexes', curr),
                            os.path.join(dbt.path, '_indexes', curr))
    dbt.open()
    for c in dbs.all('id'):
        del c['_rev']
        dbt.insert(c)
    return True


if __name__ == '__main__':
    import sys
    migrate(sys.argv[1], sys.argv[2])
