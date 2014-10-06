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

from threading import RLock

from CodernityDB3.env import cdb_environment

cdb_environment['mode'] = "threads"
cdb_environment['rlock_obj'] = RLock


from .database_safe_shared import SafeDatabase


class ThreadSafeDatabase(SafeDatabase):
    """
    Thread safe version of CodernityDB that uses several lock objects,
    on different methods / different indexes etc. It's completely different
    implementation of locking than SuperThreadSafe one.
    """
    pass
