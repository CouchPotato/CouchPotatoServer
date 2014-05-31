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


import re
import tokenize
import token
import uuid


class IndexCreatorException(Exception):
    def __init__(self, ex, line=None):
        self.ex = ex
        self.line = line

    def __str__(self):
        if self.line:
            return repr(self.ex + "(in line: %d)" % self.line)
        return repr(self.ex)


class IndexCreatorFunctionException(IndexCreatorException):
    pass


class IndexCreatorValueException(IndexCreatorException):
    pass


class Parser(object):
    def __init__(self):
        pass

    def parse(self, data, name=None):
        if not name:
            self.name = "_" + uuid.uuid4().hex
        else:
            self.name = name

        self.ind = 0
        self.stage = 0
        self.logic = ['and', 'or', 'in']
        self.logic2 = ['&', '|']
        self.allowed_props = {'TreeBasedIndex': ['type', 'name', 'key_format', 'node_capacity', 'pointer_format', 'meta_format'],
                              'HashIndex': ['type', 'name', 'key_format', 'hash_lim', 'entry_line_format'],
                              'MultiHashIndex': ['type', 'name', 'key_format', 'hash_lim', 'entry_line_format'],
                              'MultiTreeBasedIndex': ['type', 'name', 'key_format', 'node_capacity', 'pointer_format', 'meta_format']
                              }
        self.funcs = {'md5': (['md5'], ['.digest()']),
                      'len': (['len'], []),
                      'str': (['str'], []),
                      'fix_r': (['self.fix_r'], []),
                      'prefix': (['self.prefix'], []),
                      'infix': (['self.infix'], []),
                      'suffix': (['self.suffix'], [])
                      }
        self.handle_int_imports = {'infix': "from itertools import izip\n"}

        self.funcs_with_body = {'fix_r':
                                ("""    def fix_r(self,s,l):
        e = len(s)
        if e == l:
            return s
        elif e > l:
            return s[:l]
        else:
            return s.rjust(l,'_')\n""", False),
                                'prefix':
                                ("""    def prefix(self,s,m,l,f):
        t = len(s)
        if m < 1:
            m = 1
        o = set()
        if t > l:
            s = s[:l]
            t = l
        while m <= t:
            o.add(s.rjust(f,'_'))
            s = s[:-1]
            t -= 1
        return o\n""", False),
                                'suffix':
                                ("""    def suffix(self,s,m,l,f):
        t = len(s)
        if m < 1:
            m = 1
        o = set()
        if t > l:
            s = s[t-l:]
            t = len(s)
        while m <= t:
            o.add(s.rjust(f,'_'))
            s = s[1:]
            t -= 1
        return o\n""", False),
                                'infix':
                                ("""    def infix(self,s,m,l,f):
        t = len(s)
        o = set()
        for x in xrange(m - 1, l):
            t = (s, )
            for y in xrange(0, x):
                t += (s[y + 1:],)
            o.update(set(''.join(x).rjust(f, '_').lower() for x in izip(*t)))
        return o\n""", False)}
        self.none = ['None', 'none', 'null']
        self.props_assign = ['=', ':']
        self.all_adj_num_comp = {token.NUMBER: (
            token.NUMBER, token.NAME, '-', '('),
            token.NAME: (token.NUMBER, token.NAME, '-', '('),
            ')': (token.NUMBER, token.NAME, '-', '(')
        }

        self.all_adj_num_op = {token.NUMBER: (token.NUMBER, token.NAME, '('),
                               token.NAME: (token.NUMBER, token.NAME, '('),
                               ')': (token.NUMBER, token.NAME, '(')
                               }
        self.allowed_adjacent = {
            "<=": self.all_adj_num_comp,
            ">=": self.all_adj_num_comp,
            ">": self.all_adj_num_comp,
            "<": self.all_adj_num_comp,

            "==": {token.NUMBER: (token.NUMBER, token.NAME, '('),
                   token.NAME: (token.NUMBER, token.NAME, token.STRING, '('),
                   token.STRING: (token.NAME, token.STRING, '('),
                   ')': (token.NUMBER, token.NAME, token.STRING, '('),
                   ']': (token.NUMBER, token.NAME, token.STRING, '(')
                   },

            "+": {token.NUMBER: (token.NUMBER, token.NAME, '('),
                  token.NAME: (token.NUMBER, token.NAME, token.STRING, '('),
                  token.STRING: (token.NAME, token.STRING, '('),
                  ')': (token.NUMBER, token.NAME, token.STRING, '('),
                  ']': (token.NUMBER, token.NAME, token.STRING, '(')
                  },

            "-": {token.NUMBER: (token.NUMBER, token.NAME, '('),
                  token.NAME: (token.NUMBER, token.NAME, '('),
                  ')': (token.NUMBER, token.NAME, '('),
                  '<': (token.NUMBER, token.NAME, '('),
                  '>': (token.NUMBER, token.NAME, '('),
                  '<=': (token.NUMBER, token.NAME, '('),
                  '>=': (token.NUMBER, token.NAME, '('),
                  '==': (token.NUMBER, token.NAME, '('),
                  ']': (token.NUMBER, token.NAME, '(')
                  },
            "*": self.all_adj_num_op,
            "/": self.all_adj_num_op,
            "%": self.all_adj_num_op,
            ",": {token.NUMBER: (token.NUMBER, token.NAME, token.STRING, '{', '[', '('),
                  token.NAME: (token.NUMBER, token.NAME, token.STRING, '(', '{', '['),
                  token.STRING: (token.NAME, token.STRING, token.NUMBER, '(', '{', '['),
                  ')': (token.NUMBER, token.NAME, token.STRING, '(', '{', '['),
                  ']': (token.NUMBER, token.NAME, token.STRING, '(', '{', '['),
                  '}': (token.NUMBER, token.NAME, token.STRING, '(', '{', '[')
                  }
        }

        def is_num(s):
            m = re.search('[^0-9*()+\-\s/]+', s)
            return not m

        def is_string(s):
            m = re.search('\s*(?P<a>[\'\"]+).*?(?P=a)\s*', s)
            return m
        data = re.split('make_key_value\:', data)

        if len(data) < 2:
            raise IndexCreatorFunctionException(
                "Couldn't find a definition of make_key_value function!\n")

        spl1 = re.split('make_key\:', data[0])
        spl2 = re.split('make_key\:', data[1])

        self.funcs_rev = False

        if len(spl1) > 1:
            data = [spl1[0]] + [data[1]] + [spl1[1]]
            self.funcs_rev = True
        elif len(spl2) > 1:
            data = [data[0]] + spl2
        else:
            data.append("key")

        if data[1] == re.search('\s*', data[1], re.S | re.M).group(0):
            raise IndexCreatorFunctionException("Empty function body ",
                                                len(re.split('\n', data[0])) + (len(re.split('\n', data[2])) if self.funcs_rev else 1) - 1)
        if data[2] == re.search('\s*', data[2], re.S | re.M).group(0):
            raise IndexCreatorFunctionException("Empty function body ",
                                                len(re.split('\n', data[0])) + (1 if self.funcs_rev else len(re.split('\n', data[1]))) - 1)
        if data[0] == re.search('\s*', data[0], re.S | re.M).group(0):
            raise IndexCreatorValueException("You didn't set any properity or you set them not at the begining of the code\n")

        data = [re.split(
            '\n', data[0]), re.split('\n', data[1]), re.split('\n', data[2])]
        self.cnt_lines = (len(data[0]), len(data[1]), len(data[2]))
        ind = 0
        self.predata = data
        self.data = [[], [], []]
        for i, v in enumerate(self.predata[0]):
            for k, w in enumerate(self.predata[0][i]):
                if self.predata[0][i][k] in self.props_assign:
                    if not is_num(self.predata[0][i][k + 1:]) and self.predata[0][i].strip()[:4] != 'type' and self.predata[0][i].strip()[:4] != 'name':
                        s = self.predata[0][i][k + 1:]
                        self.predata[0][i] = self.predata[0][i][:k + 1]

                        m = re.search('\s+', s.strip())
                        if not is_string(s) and not m:
                            s = "'" + s.strip() + "'"
                        self.predata[0][i] += s
                        break

        for n, i in enumerate(self.predata):
            for k in i:
                k = k.strip()
                if k:
                    self.data[ind].append(k)
                    self.check_enclosures(k, n)
            ind += 1

        return self.parse_ex()

    def readline(self, stage):
        def foo():
            if len(self.data[stage]) <= self.ind:
                self.ind = 0
                return ""
            else:
                self.ind += 1
                return self.data[stage][self.ind - 1]
        return foo

    def add(self, l, i):
        def add_aux(*args):
            # print args,self.ind
            if len(l[i]) < self.ind:
                l[i].append([])
            l[i][self.ind - 1].append(args)
        return add_aux

    def parse_ex(self):
        self.index_name = ""
        self.index_type = ""
        self.curLine = -1
        self.con = -1
        self.brackets = -1
        self.curFunc = None
        self.colons = 0
        self.line_cons = ([], [], [])
        self.pre_tokens = ([], [], [])
        self.known_dicts_in_mkv = []
        self.prop_name = True
        self.prop_assign = False
        self.is_one_arg_enough = False
        self.funcs_stack = []
        self.last_line = [-1, -1, -1]
        self.props_set = []
        self.custom_header = set()

        self.tokens = []
        self.tokens_head = ['# %s\n' % self.name, 'class %s(' % self.name, '):\n', '    def __init__(self, *args, **kwargs):        ']

        for i in xrange(3):
            tokenize.tokenize(self.readline(i), self.add(self.pre_tokens, i))
            # tokenize treats some keyword not in the right way, thats why we
            # have to change some of them
            for nk, k in enumerate(self.pre_tokens[i]):
                for na, a in enumerate(k):
                    if a[0] == token.NAME and a[1] in self.logic:
                        self.pre_tokens[i][nk][
                            na] = (token.OP, a[1], a[2], a[3], a[4])

        for i in self.pre_tokens[1]:
            self.line_cons[1].append(self.check_colons(i, 1))
            self.check_adjacents(i, 1)
            if self.check_for_2nd_arg(i) == -1 and not self.is_one_arg_enough:
                raise IndexCreatorValueException("No 2nd value to return (did u forget about ',None'?", self.cnt_line_nr(i[0][4], 1))
            self.is_one_arg_enough = False

        for i in self.pre_tokens[2]:
            self.line_cons[2].append(self.check_colons(i, 2))
            self.check_adjacents(i, 2)

        for i in self.pre_tokens[0]:
            self.handle_prop_line(i)

        self.cur_brackets = 0
        self.tokens += ['\n        super(%s, self).__init__(*args, **kwargs)\n    def make_key_value(self, data):        ' % self.name]

        for i in self.pre_tokens[1]:
            for k in i:
                self.handle_make_value(*k)

        self.curLine = -1
        self.con = -1
        self.cur_brackets = 0
        self.tokens += ['\n    def make_key(self, key):']

        for i in self.pre_tokens[2]:
            for k in i:
                self.handle_make_key(*k)

        if self.index_type == "":
            raise IndexCreatorValueException("Missing index type definition\n")
        if self.index_name == "":
            raise IndexCreatorValueException("Missing index name\n")

        self.tokens_head[0] = "# " + self.index_name + "\n" + \
            self.tokens_head[0]

        for i in self.funcs_with_body:
            if self.funcs_with_body[i][1]:
                self.tokens_head.insert(4, self.funcs_with_body[i][0])

        if None in self.custom_header:
            self.custom_header.remove(None)
        if self.custom_header:
            s = '    custom_header = """'
            for i in self.custom_header:
                s += i
            s += '"""\n'
            self.tokens_head.insert(4, s)

        if self.index_type in self.allowed_props:
            for i in self.props_set:
                if i not in self.allowed_props[self.index_type]:
                    raise IndexCreatorValueException("Properity %s is not allowed for index type: %s" % (i, self.index_type))

        # print "".join(self.tokens_head)
        # print "----------"
        # print (" ".join(self.tokens))
        return "".join(self.custom_header), "".join(self.tokens_head) + (" ".join(self.tokens))

    # has to be run BEFORE tokenize
    def check_enclosures(self, d, st):
        encs = []
        contr = {'(': ')', '{': '}', '[': ']', "'": "'", '"': '"'}
        ends = [')', '}', ']', "'", '"']
        for i in d:
            if len(encs) > 0 and encs[-1] in ['"', "'"]:
                if encs[-1] == i:
                    del encs[-1]
            elif i in contr:
                encs += [i]
            elif i in ends:
                if len(encs) < 1 or contr[encs[-1]] != i:
                    raise IndexCreatorValueException("Missing opening enclosure for \'%s\'" % i, self.cnt_line_nr(d, st))
                del encs[-1]

        if len(encs) > 0:
            raise IndexCreatorValueException("Missing closing enclosure for \'%s\'" % encs[0], self.cnt_line_nr(d, st))

    def check_adjacents(self, d, st):
        def std_check(d, n):
            if n == 0:
                prev = -1
            else:
                prev = d[n - 1][1] if d[n - 1][0] == token.OP else d[n - 1][0]

            cur = d[n][1] if d[n][0] == token.OP else d[n][0]

            # there always is an endmarker at the end, but this is a precaution
            if n + 2 > len(d):
                nex = -1
            else:
                nex = d[n + 1][1] if d[n + 1][0] == token.OP else d[n + 1][0]

            if prev not in self.allowed_adjacent[cur]:
                raise IndexCreatorValueException("Wrong left value of the %s" % cur, self.cnt_line_nr(line, st))

            # there is an assumption that whole data always ends with 0 marker, the idea prolly needs a rewritting to allow more whitespaces
            # between tokens, so it will be handled anyway
            elif nex not in self.allowed_adjacent[cur][prev]:
                raise IndexCreatorValueException("Wrong right value of the %s" % cur, self.cnt_line_nr(line, st))

        for n, (t, i, _, _, line) in enumerate(d):
            if t == token.NAME or t == token.STRING:
                if n + 1 < len(d) and d[n + 1][0] in [token.NAME, token.STRING]:
                    raise IndexCreatorValueException("Did you forget about an operator in between?", self.cnt_line_nr(line, st))
            elif i in self.allowed_adjacent:
                std_check(d, n)

    def check_colons(self, d, st):
        cnt = 0
        br = 0

        def check_ret_args_nr(a, s):
            c_b_cnt = 0
            s_b_cnt = 0
            n_b_cnt = 0
            comas_cnt = 0
            for _, i, _, _, line in a:

                if c_b_cnt == n_b_cnt == s_b_cnt == 0:
                    if i == ',':
                        comas_cnt += 1
                        if (s == 1 and comas_cnt > 1) or (s == 2 and comas_cnt > 0):
                            raise IndexCreatorFunctionException("Too much arguments to return", self.cnt_line_nr(line, st))
                        if s == 0 and comas_cnt > 0:
                            raise IndexCreatorValueException("A coma here doesn't make any sense", self.cnt_line_nr(line, st))

                    elif i == ':':
                            if s == 0:
                                raise IndexCreatorValueException("A colon here doesn't make any sense", self.cnt_line_nr(line, st))
                            raise IndexCreatorFunctionException("Two colons don't make any sense", self.cnt_line_nr(line, st))

                if i == '{':
                    c_b_cnt += 1
                elif i == '}':
                    c_b_cnt -= 1
                elif i == '(':
                    n_b_cnt += 1
                elif i == ')':
                    n_b_cnt -= 1
                elif i == '[':
                    s_b_cnt += 1
                elif i == ']':
                    s_b_cnt -= 1

        def check_if_empty(a):
            for i in a:
                if i not in [token.NEWLINE, token.INDENT, token.ENDMARKER]:
                    return False
            return True
        if st == 0:
            check_ret_args_nr(d, st)
            return

        for n, i in enumerate(d):
            if i[1] == ':':
                if br == 0:
                    if len(d) < n or check_if_empty(d[n + 1:]):
                        raise IndexCreatorValueException(
                            "Empty return value", self.cnt_line_nr(i[4], st))
                    elif len(d) >= n:
                        check_ret_args_nr(d[n + 1:], st)
                    return cnt
                else:
                    cnt += 1
            elif i[1] == '{':
                br += 1
            elif i[1] == '}':
                br -= 1
        check_ret_args_nr(d, st)
        return -1

    def check_for_2nd_arg(self, d):
        c_b_cnt = 0  # curly brackets counter '{}'
        s_b_cnt = 0  # square brackets counter '[]'
        n_b_cnt = 0  # normal brackets counter '()'

        def check_2nd_arg(d, ind):
            d = d[ind[0]:]
            for t, i, (n, r), _, line in d:
                if i == '{' or i is None:
                    return 0
                elif t == token.NAME:
                    self.known_dicts_in_mkv.append((i, (n, r)))
                    return 0
                elif t == token.STRING or t == token.NUMBER:
                    raise IndexCreatorValueException("Second return value of make_key_value function has to be a dictionary!", self.cnt_line_nr(line, 1))

        for ind in enumerate(d):
            t, i, _, _, _ = ind[1]
            if s_b_cnt == n_b_cnt == c_b_cnt == 0:
                if i == ',':
                    return check_2nd_arg(d, ind)
                elif (t == token.NAME and i not in self.funcs) or i == '{':
                    self.is_one_arg_enough = True

            if i == '{':
                c_b_cnt += 1
                self.is_one_arg_enough = True
            elif i == '}':
                c_b_cnt -= 1
            elif i == '(':
                n_b_cnt += 1
            elif i == ')':
                n_b_cnt -= 1
            elif i == '[':
                s_b_cnt += 1
            elif i == ']':
                s_b_cnt -= 1
        return -1

    def cnt_line_nr(self, l, stage):
        nr = -1
        for n, i in enumerate(self.predata[stage]):
            # print i,"|||",i.strip(),"|||",l
            if l == i.strip():
                nr = n
        if nr == -1:
            return -1

        if stage == 0:
            return nr + 1
        elif stage == 1:
            return nr + self.cnt_lines[0] + (self.cnt_lines[2] - 1 if self.funcs_rev else 0)
        elif stage == 2:
            return nr + self.cnt_lines[0] + (self.cnt_lines[1] - 1 if not self.funcs_rev else 0)

        return -1

    def handle_prop_line(self, d):
        d_len = len(d)
        if d[d_len - 1][0] == token.ENDMARKER:
            d_len -= 1

        if d_len < 3:
            raise IndexCreatorValueException("Can't handle properity assingment ", self.cnt_line_nr(d[0][4], 0))

        if not d[1][1] in self.props_assign:
            raise IndexCreatorValueException(
                "Did you forget : or =?", self.cnt_line_nr(d[0][4], 0))

        if d[0][0] == token.NAME or d[0][0] == token.STRING:
            if d[0][1] in self.props_set:
                raise IndexCreatorValueException("Properity %s is set more than once" % d[0][1], self.cnt_line_nr(d[0][4], 0))
            self.props_set += [d[0][1]]
            if d[0][1] == "type" or d[0][1] == "name":
                t, tk, _, _, line = d[2]

                if d_len > 3:
                    raise IndexCreatorValueException(
                        "Wrong value to assign", self.cnt_line_nr(line, 0))

                if t == token.STRING:
                    m = re.search('\s*(?P<a>[\'\"]+)(.*?)(?P=a)\s*', tk)
                    if m:
                        tk = m.groups()[1]
                elif t != token.NAME:
                    raise IndexCreatorValueException(
                        "Wrong value to assign", self.cnt_line_nr(line, 0))

                if d[0][1] == "type":
                    if d[2][1] == "TreeBasedIndex":
                        self.custom_header.add("from CodernityDB.tree_index import TreeBasedIndex\n")
                    elif d[2][1] == "MultiTreeBasedIndex":
                        self.custom_header.add("from CodernityDB.tree_index import MultiTreeBasedIndex\n")
                    elif d[2][1] == "MultiHashIndex":
                        self.custom_header.add("from CodernityDB.hash_index import MultiHashIndex\n")
                    self.tokens_head.insert(2, tk)
                    self.index_type = tk
                else:
                    self.index_name = tk
                return
            else:
                self.tokens += ['\n        kwargs["' + d[0][1] + '"]']
        else:
            raise IndexCreatorValueException("Can't handle properity assingment ", self.cnt_line_nr(d[0][4], 0))

        self.tokens += ['=']

        self.check_adjacents(d[2:], 0)
        self.check_colons(d[2:], 0)

        for i in d[2:]:
            self.tokens += [i[1]]

    def generate_func(self, t, tk, pos_start, pos_end, line, hdata, stage):
        if self.last_line[stage] != -1 and pos_start[0] > self.last_line[stage] and line != '':
            raise IndexCreatorFunctionException("This line will never be executed!", self.cnt_line_nr(line, stage))
        if t == 0:
            return

        if pos_start[1] == 0:
            if self.line_cons[stage][pos_start[0] - 1] == -1:
                self.tokens += ['\n        return']
                self.last_line[stage] = pos_start[0]
            else:
                self.tokens += ['\n        if']
        elif tk == ':' and self.line_cons[stage][pos_start[0] - 1] > -1:
            if self.line_cons[stage][pos_start[0] - 1] == 0:
                self.tokens += [':\n            return']
                return
            self.line_cons[stage][pos_start[0] - 1] -= 1

        if tk in self.logic2:
            # print tk
            if line[pos_start[1] - 1] != tk and line[pos_start[1] + 1] != tk:
                self.tokens += [tk]
            if line[pos_start[1] - 1] != tk and line[pos_start[1] + 1] == tk:
                if tk == '&':
                    self.tokens += ['and']
                else:
                    self.tokens += ['or']
            return

        if self.brackets != 0:
            def search_through_known_dicts(a):
                for i, (n, r) in self.known_dicts_in_mkv:
                    if i == tk and r > pos_start[1] and n == pos_start[0] and hdata == 'data':
                        return True
                return False

            if t == token.NAME and len(self.funcs_stack) > 0 and self.funcs_stack[-1][0] == 'md5' and search_through_known_dicts(tk):
                raise IndexCreatorValueException("Second value returned by make_key_value for sure isn't a dictionary ", self.cnt_line_nr(line, 1))

        if tk == ')':
            self.cur_brackets -= 1
            if len(self.funcs_stack) > 0 and self.cur_brackets == self.funcs_stack[-1][1]:
                self.tokens += [tk]
                self.tokens += self.funcs[self.funcs_stack[-1][0]][1]
                del self.funcs_stack[-1]
                return
        if tk == '(':
            self.cur_brackets += 1

        if tk in self.none:
            self.tokens += ['None']
            return

        if t == token.NAME and tk not in self.logic and tk != hdata:
            if tk not in self.funcs:
                self.tokens += [hdata + '["' + tk + '"]']
            else:
                self.tokens += self.funcs[tk][0]
                if tk in self.funcs_with_body:
                    self.funcs_with_body[tk] = (
                        self.funcs_with_body[tk][0], True)
                self.custom_header.add(self.handle_int_imports.get(tk))
                self.funcs_stack += [(tk, self.cur_brackets)]
        else:
            self.tokens += [tk]

    def handle_make_value(self, t, tk, pos_start, pos_end, line):
        self.generate_func(t, tk, pos_start, pos_end, line, 'data', 1)

    def handle_make_key(self, t, tk, pos_start, pos_end, line):
        self.generate_func(t, tk, pos_start, pos_end, line, 'key', 2)
