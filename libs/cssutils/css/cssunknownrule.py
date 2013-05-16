"""CSSUnknownRule implements DOM Level 2 CSS CSSUnknownRule."""
__all__ = ['CSSUnknownRule']
__docformat__ = 'restructuredtext'
__version__ = '$Id$'

import cssrule
import cssutils
import xml.dom

class CSSUnknownRule(cssrule.CSSRule):
    """
    Represents an at-rule not supported by this user agent, so in 
    effect all other at-rules not defined in cssutils.

    Format::

        @xxx until ';' or block {...}
    """
    def __init__(self, cssText=u'', parentRule=None, 
                 parentStyleSheet=None, readonly=False):
        """
        :param cssText:
            of type string
        """
        super(CSSUnknownRule, self).__init__(parentRule=parentRule, 
                                             parentStyleSheet=parentStyleSheet)
        self._atkeyword = None
        if cssText:
            self.cssText = cssText

        self._readonly = readonly

    def __repr__(self):
        return u"cssutils.css.%s(cssText=%r)" % (
                self.__class__.__name__,
                self.cssText)
        
    def __str__(self):
        return u"<cssutils.css.%s object cssText=%r at 0x%x>" % (
                self.__class__.__name__,
                self.cssText,
                id(self))

    def _getCssText(self):
        """Return serialized property cssText."""
        return cssutils.ser.do_CSSUnknownRule(self)

    def _setCssText(self, cssText):
        """
        :exceptions:
            - :exc:`~xml.dom.SyntaxErr`:
              Raised if the specified CSS string value has a syntax error and
              is unparsable.
            - :exc:`~xml.dom.InvalidModificationErr`:
              Raised if the specified CSS string value represents a different
              type of rule than the current one.
            - :exc:`~xml.dom.HierarchyRequestErr`:
              Raised if the rule cannot be inserted at this point in the
              style sheet.
            - :exc:`~xml.dom.NoModificationAllowedErr`:
              Raised if the rule is readonly.
        """
        super(CSSUnknownRule, self)._setCssText(cssText)
        tokenizer = self._tokenize2(cssText)
        attoken = self._nexttoken(tokenizer, None)
        if not attoken or self._type(attoken) != self._prods.ATKEYWORD:
            self._log.error(u'CSSUnknownRule: No CSSUnknownRule found: %s' %
                self._valuestr(cssText),
                error=xml.dom.InvalidModificationErr)
        else:
            # for closures: must be a mutable
            new = {'nesting': [], # {} [] or ()
                   'wellformed': True
                   }

            def CHAR(expected, seq, token, tokenizer=None):
                type_, val, line, col = token
                if expected != 'EOF':
                    if val in u'{[(':
                        new['nesting'].append(val)
                    elif val in u'}])':
                        opening = {u'}': u'{', u']': u'[', u')': u'('}[val]
                        try:
                            if new['nesting'][-1] == opening:
                                new['nesting'].pop()
                            else:
                                raise IndexError()
                        except IndexError:
                            new['wellformed'] = False
                            self._log.error(u'CSSUnknownRule: Wrong nesting of '
                                            u'{, [ or (.', token=token)
    
                    if val in u'};' and not new['nesting']:
                        expected = 'EOF' 
    
                    seq.append(val, type_, line=line, col=col)
                    return expected
                else:
                    new['wellformed'] = False
                    self._log.error(u'CSSUnknownRule: Expected end of rule.',
                                    token=token)
                    return expected

            def FUNCTION(expected, seq, token, tokenizer=None):
                # handled as opening (
                type_, val, line, col = token
                val = self._tokenvalue(token)
                if expected != 'EOF':
                    new['nesting'].append(u'(')
                    seq.append(val, type_, line=line, col=col)
                    return expected
                else:
                    new['wellformed'] = False
                    self._log.error(u'CSSUnknownRule: Expected end of rule.',
                                    token=token)
                    return expected                

            def EOF(expected, seq, token, tokenizer=None):
                "close all blocks and return 'EOF'"
                for x in reversed(new['nesting']):
                    closing = {u'{': u'}', u'[': u']', u'(': u')'}[x]
                    seq.append(closing, closing)
                new['nesting'] = []
                return 'EOF'
                
            def INVALID(expected, seq, token, tokenizer=None):
                # makes rule invalid
                self._log.error(u'CSSUnknownRule: Bad syntax.',
                                token=token, error=xml.dom.SyntaxErr)
                new['wellformed'] = False
                return expected

            def STRING(expected, seq, token, tokenizer=None):
                type_, val, line, col = token
                val = self._stringtokenvalue(token)
                if expected != 'EOF':
                    seq.append(val, type_, line=line, col=col)
                    return expected
                else:
                    new['wellformed'] = False
                    self._log.error(u'CSSUnknownRule: Expected end of rule.',
                                    token=token)
                    return expected                

            def URI(expected, seq, token, tokenizer=None):
                type_, val, line, col = token
                val = self._uritokenvalue(token)
                if expected != 'EOF':
                    seq.append(val, type_, line=line, col=col)
                    return expected
                else:
                    new['wellformed'] = False
                    self._log.error(u'CSSUnknownRule: Expected end of rule.',
                                    token=token)
                    return expected                

            def default(expected, seq, token, tokenizer=None):
                type_, val, line, col = token
                if expected != 'EOF':
                    seq.append(val, type_, line=line, col=col)
                    return expected
                else:
                    new['wellformed'] = False
                    self._log.error(u'CSSUnknownRule: Expected end of rule.',
                                    token=token)
                    return expected                

            # unknown : ATKEYWORD S* ... ; | }
            newseq = self._tempSeq()
            wellformed, expected = self._parse(expected=None,
                seq=newseq, tokenizer=tokenizer,
                productions={'CHAR': CHAR,
                             'EOF': EOF,
                             'FUNCTION': FUNCTION,
                             'INVALID': INVALID,
                             'STRING': STRING,
                             'URI': URI,
                             'S': default # overwrite default default!
                }, 
                default=default,
                new=new)

            # wellformed set by parse
            wellformed = wellformed and new['wellformed']
            
            # post conditions
            if expected != 'EOF':
                wellformed = False
                self._log.error(u'CSSUnknownRule: No ending ";" or "}" found: '
                                u'%r' % self._valuestr(cssText))
            elif new['nesting']:
                wellformed = False
                self._log.error(u'CSSUnknownRule: Unclosed "{", "[" or "(": %r'
                                % self._valuestr(cssText))

            # set all
            if wellformed:
                self.atkeyword = self._tokenvalue(attoken)
                self._setSeq(newseq)

    cssText = property(fget=_getCssText, fset=_setCssText,
                       doc=u"(DOM) The parsable textual representation.")
    
    type = property(lambda self: self.UNKNOWN_RULE, 
                    doc=u"The type of this rule, as defined by a CSSRule "
                        u"type constant.")
    
    wellformed = property(lambda self: bool(self.atkeyword))
    