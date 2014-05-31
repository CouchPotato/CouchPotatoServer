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

from random import getrandbits, randrange
import uuid


class NONE:
    """
    It's inteded to be None but different,
    for internal use only!
    """
    pass


def random_hex_32():
    return uuid.UUID(int=getrandbits(128), version=4).hex


def random_hex_4(*args, **kwargs):
    return '%04x' % randrange(256 ** 2)
