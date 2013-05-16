"""MarginRule implements DOM Level 2 CSS MarginRule."""
__all__ = ['MarginRule']
__docformat__ = 'restructuredtext'
__version__ = '$Id$'

from cssutils.prodparser import *
from cssstyledeclaration import CSSStyleDeclaration
import cssrule
import cssutils
import xml.dom

class MarginRule(cssrule.CSSRule):
    """
    A margin at-rule consists of an ATKEYWORD that identifies the margin box
    (e.g. '@top-left') and a block of declarations (said to be in the margin
    context).

    Format::
        
        margin :
               margin_sym S* '{' declaration [ ';' S* declaration? ]* '}' S*
               ;
        
        margin_sym :
               TOPLEFTCORNER_SYM | 
               TOPLEFT_SYM | 
               TOPCENTER_SYM | 
               TOPRIGHT_SYM | 
               TOPRIGHTCORNER_SYM |
               BOTTOMLEFTCORNER_SYM | 
               BOTTOMLEFT_SYM | 
               BOTTOMCENTER_SYM | 
               BOTTOMRIGHT_SYM |
               BOTTOMRIGHTCORNER_SYM |
               LEFTTOP_SYM |
               LEFTMIDDLE_SYM |
               LEFTBOTTOM_SYM |
               RIGHTTOP_SYM |
               RIGHTMIDDLE_SYM |
               RIGHTBOTTOM_SYM 
               ;
        
    e.g.::
    
        @top-left {
            content: "123";
            }
    """
    margins = ['@top-left-corner',
               '@top-left',
               '@top-center',
               '@top-right',
               '@top-right-corner',
               '@bottom-left-corner',
               '@bottom-left',
               '@bottom-center',
               '@bottom-right',
               '@bottom-right-corner',
               '@left-top',
               '@left-middle',
               '@left-bottom',
               '@right-top',
               '@right-middle',
               '@right-bottom'
               ]
    
    def __init__(self, margin=None, style=None, parentRule=None, 
                 parentStyleSheet=None, readonly=False):
        """
        :param atkeyword:
            The margin area, e.g. '@top-left' for this rule
        :param style:
            CSSStyleDeclaration for this MarginRule
        """
        super(MarginRule, self).__init__(parentRule=parentRule, 
                                         parentStyleSheet=parentStyleSheet)
        
        self._atkeyword = self._keyword = None
        
        if margin:
            self.margin = margin
            
        if style:
            self.style = style
        else:
            self.style = CSSStyleDeclaration(parentRule=self)
        
        self._readonly = readonly

    def _setMargin(self, margin):
        """Check if new keyword fits the rule it is used for."""
        n = self._normalize(margin)
        
        if n not in MarginRule.margins:
            self._log.error(u'Invalid margin @keyword for this %s rule: %r' %
                            (self.margin, margin),
                            error=xml.dom.InvalidModificationErr)
    
        else:
            self._atkeyword = n
            self._keyword = margin

    margin = property(lambda self: self._atkeyword, _setMargin,
                      doc=u"Margin area of parent CSSPageRule. "
                          u"`margin` and `atkeyword` are both normalized "
                          u"@keyword of the @rule.")

    atkeyword = margin 

    def __repr__(self):
        return u"cssutils.css.%s(margin=%r, style=%r)" % (self.__class__.__name__,
                                                          self.margin, 
                                                          self.style.cssText)

    def __str__(self):
        return u"<cssutils.css.%s object margin=%r style=%r "\
               u"at 0x%x>" % (self.__class__.__name__,
                              self.margin,
                              self.style.cssText,
                              id(self))

    def _getCssText(self):
        """Return serialized property cssText."""
        return cssutils.ser.do_MarginRule(self)

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
        super(MarginRule, self)._setCssText(cssText)
                
        # TEMP: all style tokens are saved in store to fill styledeclaration
        # TODO: resolve when all generators
        styletokens = Prod(name='styletokens',
                           match=lambda t, v: v != u'}',
                           #toSeq=False,
                           toStore='styletokens',
                           storeToken=True 
                           )
                
        prods = Sequence(Prod(name='@ margin', 
                              match=lambda t, v: 
                                t == 'ATKEYWORD' and 
                                self._normalize(v) in MarginRule.margins,
                              toStore='margin'
                              # TODO?
                              #, exception=xml.dom.InvalidModificationErr 
                              ),
                         PreDef.char('OPEN', u'{'),
                         Sequence(Choice(PreDef.unknownrule(toStore='@'), 
                                         styletokens),
                                  minmax=lambda: (0, None)
                         ),
                         PreDef.char('CLOSE', u'}', stopAndKeep=True)
                )
        # parse
        ok, seq, store, unused = ProdParser().parse(cssText,
                                                    u'MarginRule',
                                                    prods)
        
        if ok:
            # TODO: use seq for serializing instead of fixed stuff?
            self._setSeq(seq)
            
            if 'margin' in store:
                # may raise:
                self.margin = store['margin'].value
            else:
                self._log.error(u'No margin @keyword for this %s rule' %
                                self.margin,
                                error=xml.dom.InvalidModificationErr)
            
            # new empty style
            self.style = CSSStyleDeclaration(parentRule=self)
            
            if 'styletokens' in store:
                # may raise:
                self.style.cssText = store['styletokens']
            
                
    cssText = property(fget=_getCssText, fset=_setCssText,
                       doc=u"(DOM) The parsable textual representation.")
    
    def _setStyle(self, style):
        """
        :param style: A string or CSSStyleDeclaration which replaces the
            current style object.
        """
        self._checkReadonly()
        if isinstance(style, basestring):
            self._style = CSSStyleDeclaration(cssText=style, parentRule=self)
        else:
            style._parentRule = self
            self._style = style

    style = property(lambda self: self._style, _setStyle,
                     doc=u"(DOM) The declaration-block of this rule set.")
    
    type = property(lambda self: self.MARGIN_RULE, 
                    doc=u"The type of this rule, as defined by a CSSRule "
                        u"type constant.")
    
    wellformed = property(lambda self: bool(self.atkeyword))
    