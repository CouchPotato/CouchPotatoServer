# CSSPrefixer
# Copyright 2010-2012 Greg V. <floatboth@me.com>

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import re
import cssutils

prefixRegex = re.compile('^(-o-|-ms-|-moz-|-webkit-)')


class BaseReplacementRule(object):
    vendor_prefixes = ['moz', 'webkit']

    def __init__(self, prop):
        self.prop = prop

    def get_prefixed_props(self, filt):
        for prefix in [p for p in self.vendor_prefixes if p in filt]:
            yield cssutils.css.Property(
                    name='-%s-%s' % (prefix, self.prop.name),
                    value=self.prop.value,
                    priority=self.prop.priority
                    )

    @staticmethod
    def should_prefix():
        return True


class FullReplacementRule(BaseReplacementRule):
    vendor_prefixes = sorted(BaseReplacementRule.vendor_prefixes + ['o', 'ms'])


class BaseAndIEReplacementRule(BaseReplacementRule):
    vendor_prefixes = sorted(BaseReplacementRule.vendor_prefixes + ['ms'])


class BaseAndOperaReplacementRule(BaseReplacementRule):
    vendor_prefixes = sorted(BaseReplacementRule.vendor_prefixes + ['o'])


class WebkitReplacementRule(BaseReplacementRule):
    vendor_prefixes = ['webkit']


class OperaAndIEReplacementRule(BaseReplacementRule):
    vendor_prefixes = ['ms', 'o']


class MozReplacementRule(BaseReplacementRule):
    vendor_prefixes = ['moz']


class BorderRadiusReplacementRule(BaseReplacementRule):
    """
    Mozilla's Gecko engine uses different syntax for rounded corners.
    """
    vendor_prefixes = ['webkit']

    def get_prefixed_props(self, filt):
        for prop in BaseReplacementRule.get_prefixed_props(self, filt):
            yield prop
        if 'moz' in filt:
            name = '-moz-' + self.prop.name.replace('top-left-radius', 'radius-topleft') \
                   .replace('top-right-radius', 'radius-topright') \
                   .replace('bottom-right-radius', 'radius-bottomright') \
                   .replace('bottom-left-radius', 'radius-bottomleft')
            yield cssutils.css.Property(
                    name=name,
                    value=self.prop.value,
                    priority=self.prop.priority
                    )


class DisplayReplacementRule(BaseReplacementRule):
    """
    Flexible Box Model stuff.
    CSSUtils parser doesn't support duplicate properties, so that's dirty.
    """
    def get_prefixed_props(self, filt):
        if self.prop.value == 'box':  # only add prefixes if the value is box
            for prefix in [p for p in self.vendor_prefixes if p in filt]:
                yield cssutils.css.Property(
                        name='display',
                        value='-%s-box' % prefix,
                        priority=self.prop.priority
                        )


class TransitionReplacementRule(BaseReplacementRule):
    vendor_prefixes = ['moz', 'o', 'webkit']

    def __get_prefixed_prop(self, prefix=None):
        name = self.prop.name
        if prefix:
            name = '-%s-%s' % (prefix, self.prop.name)
        newValues = []
        for value in self.prop.value.split(','):
            parts = value.strip().split(' ')
            parts[0] = prefixRegex.sub('', parts[0])
            if parts[0] in rules and prefix and rules[parts[0]].should_prefix():
                parts[0] = '-%s-%s' % (prefix, parts[0])
            newValues.append(' '.join(parts))
        return cssutils.css.Property(
                name=name,
                value=', '.join(newValues),
                priority=self.prop.priority
                )

    def get_prefixed_props(self, filt):
        for prefix in [p for p in self.vendor_prefixes if p in filt]:
            yield self.__get_prefixed_prop(prefix)

    def get_base_prop(self):
        return self.__get_prefixed_prop()


class GradientReplacementRule(BaseReplacementRule):
    vendor_prefixes = ['moz', 'o', 'webkit']

    def __iter_values(self):
        valueSplit = self.prop.value.split(',')
        index = 0
        # currentString = ''
        while(True):
            if index >= len(valueSplit):
                break
            rawValue = valueSplit[index].strip()
            snip = prefixRegex.sub('', rawValue)
            if snip.startswith('linear-gradient'):
                values = [re.sub('^linear-gradient\(', '', snip)]
                if valueSplit[index + 1].strip().endswith(')'):
                    values.append(re.sub('\)+$', '', valueSplit[index + 1].strip()))
                else:
                    values.append(valueSplit[index + 1].strip())
                    values.append(re.sub('\)+$', '', valueSplit[index + 2].strip()))
                if len(values) == 2:
                    yield {
                        'start': values[0],
                        'end': values[1]
                        }
                else:
                    yield {
                        'pos': values[0],
                        'start': values[1],
                        'end': values[2]
                        }
                index += len(values)
            elif snip.startswith('gradient'):
                yield {
                    'start': re.sub('\)+$', '', valueSplit[index + 4].strip()),
                    'end': re.sub('\)+$', '', valueSplit[index + 6].strip()),
                    }
                index += 7
            else:
                # not a gradient so just yield the raw string
                yield rawValue
                index += 1

    def __get_prefixed_prop(self, values, prefix=None):
        gradientName = 'linear-gradient'
        if prefix:
            gradientName = '-%s-%s' % (prefix, gradientName)
        newValues = []
        for value in values:
            if isinstance(value, dict):
                if 'pos' in value:
                    newValues.append(gradientName + '(%(pos)s, %(start)s, %(end)s)' % value)
                else:
                    newValues.append(gradientName + '(%(start)s, %(end)s)' % value)
            else:
                newValues.append(value)
        return cssutils.css.Property(
                name=self.prop.name,
                value=', '.join(newValues),
                priority=self.prop.priority
                )

    def get_prefixed_props(self, filt):
        values = list(self.__iter_values())
        needPrefix = False
        for value in values:  # check if there are any gradients
            if isinstance(value, dict):
                needPrefix = True
                break
        if needPrefix:
            for prefix in [p for p in self.vendor_prefixes if p in filt]:
                yield self.__get_prefixed_prop(values, prefix)
                if prefix == 'webkit':
                    newValues = []
                    for value in values:
                        if isinstance(value, dict):
                            newValues.append('-webkit-gradient(linear, left top, left bottom, color-stop(0, %(start)s), color-stop(1, %(end)s))' % value)
                        else:
                            newValues.append(value)
                    yield cssutils.css.Property(
                            name=self.prop.name,
                            value=', '.join(newValues),
                            priority=self.prop.priority
                            )
        else:
            yield None

    def get_base_prop(self):
        values = self.__iter_values()
        return self.__get_prefixed_prop(values)

rules = {
    'border-radius': BaseReplacementRule,
    'border-top-left-radius': BorderRadiusReplacementRule,
    'border-top-right-radius': BorderRadiusReplacementRule,
    'border-bottom-right-radius': BorderRadiusReplacementRule,
    'border-bottom-left-radius': BorderRadiusReplacementRule,
    'border-image': FullReplacementRule,
    'box-shadow': BaseReplacementRule,
    'box-sizing': MozReplacementRule,
    'box-orient': BaseAndIEReplacementRule,
    'box-direction': BaseAndIEReplacementRule,
    'box-ordinal-group': BaseAndIEReplacementRule,
    'box-align': BaseAndIEReplacementRule,
    'box-flex': BaseAndIEReplacementRule,
    'box-flex-group': BaseReplacementRule,
    'box-pack': BaseAndIEReplacementRule,
    'box-lines': BaseAndIEReplacementRule,
    'user-select': BaseReplacementRule,
    'user-modify': BaseReplacementRule,
    'margin-start': BaseReplacementRule,
    'margin-end': BaseReplacementRule,
    'padding-start': BaseReplacementRule,
    'padding-end': BaseReplacementRule,
    'column-count': BaseReplacementRule,
    'column-gap': BaseReplacementRule,
    'column-rule': BaseReplacementRule,
    'column-rule-color': BaseReplacementRule,
    'column-rule-style': BaseReplacementRule,
    'column-rule-width': BaseReplacementRule,
    'column-span': WebkitReplacementRule,
    'column-width': BaseReplacementRule,
    'columns': WebkitReplacementRule,

    'background-clip': WebkitReplacementRule,
    'background-origin': WebkitReplacementRule,
    'background-size': WebkitReplacementRule,
    'background-image': GradientReplacementRule,
    'background': GradientReplacementRule,

    'text-overflow': OperaAndIEReplacementRule,

    'transition': TransitionReplacementRule,
    'transition-delay': BaseAndOperaReplacementRule,
    'transition-duration': BaseAndOperaReplacementRule,
    'transition-property': TransitionReplacementRule,
    'transition-timing-function': BaseAndOperaReplacementRule,
    'transform': FullReplacementRule,
    'transform-origin': FullReplacementRule,

    'display': DisplayReplacementRule,
    'appearance': WebkitReplacementRule,
    'hyphens': BaseReplacementRule,
}
