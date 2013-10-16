# Copyright 2013 Dean Gardiner <gardiner91@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from qcond.transformers.merge import MergeTransformer
from qcond.transformers.slice import SliceTransformer
from qcond.transformers.strip_common import StripCommonTransformer


__version_info__ = ('0', '1', '0')
__version_branch__ = 'master'

__version__ = "%s%s" % (
    '.'.join(__version_info__),
    '-' + __version_branch__ if __version_branch__ else ''
)


class QueryCondenser(object):
    def __init__(self):
        self.transformers = [
            MergeTransformer(),
            SliceTransformer(),
            StripCommonTransformer()
        ]

    def distinct(self, titles):
        for transformer in self.transformers:
            titles = transformer.run(titles)

        return titles
