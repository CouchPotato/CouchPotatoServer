from pyparsing import *
IdentifierStart = oneOf(['$', '_']+list(alphas))
Identifier = Combine(IdentifierStart + Optional(Word(alphas+nums+'$_')))

_keywords = ['break', 'do', 'instanceof', 'typeof', 'case', 'else', 'new', 'var', 'catch', 'finally',
             'return', 'void', 'continue', 'for', 'switch', 'while', 'debugger', 'function', 'this',
             'with', 'default', 'if', 'throw', 'delete', 'in', 'try']

Keyword = oneOf(_keywords)


#Literals

#Bool
BooleanLiteral = oneOf(('true', 'false'))

#Null

NullLiteral = Literal('null')

#Undefined

UndefinedLiteral = Literal('undefined')

#NaN

NaNLiteral = Literal('NaN')

#Number
NonZeroDigit = oneOf(['1','2','3','4','5','6','7','8','9'])
DecimalDigit = oneOf(['0', '1','2','3','4','5','6','7','8','9'])
HexDigit = oneOf(list('0123456789abcdefABCDEF'))
DecimalDigits = Word(nums)
DecimalIntegerLiteral = Combine(NonZeroDigit+Optional(DecimalDigits)) | '0' 
SignedInteger = Combine('-'+DecimalDigits) | Combine('+'+DecimalDigits) | DecimalDigits
ExponentPart = Combine(oneOf('e', 'E')+SignedInteger)
_DecimalLiteral = (Combine(DecimalIntegerLiteral('int')+'.'+Optional(DecimalDigits('float'))+Optional(ExponentPart('exp'))) |
                  Combine('.'+DecimalDigits('float')+Optional(ExponentPart('exp'))) |
                  DecimalIntegerLiteral('int')+Optional(ExponentPart('exp')))
DecimalLiteral = Combine(_DecimalLiteral+NotAny(IdentifierStart))
HexIntegerLiteral = Combine(oneOf(('0x','0X'))+Word('0123456789abcdefABCDEF')('hex'))
NumericLiteral = Group(DecimalLiteral)('decimal') ^ Group(HexIntegerLiteral)('hex')

def js_num(num):
    res = NumericLiteral.parseString(num)
    if res.decimal:
        res = res.decimal
        cand = int(res.int if res.int else 0)+ float('0.'+res.float if res.float else 0)
        if res.exp:
            cand*= 10**int(res.exp)
        return cand
    elif res.hex:
        return int(res.hex.hex, 16)

#String
LineTerminator = White('\n', 1,1,1) | White('\r', 1,1,1)
LineTerminatorSequence = Combine(White('\r', 1,1,1)+White('\n', 1,1,1)) | White('\n', 1,1,1) | White('\r', 1,1,1)
LineContinuation  = Combine('\\'+LineTerminatorSequence)

UnicodeEscapeSequence = Combine('u'+HexDigit+HexDigit+HexDigit+HexDigit)
HexEscapeSequence = Combine('x'+HexDigit+HexDigit)
SingleEscapeCharacter = oneOf(["'", '"', '\\', 'b', 'f', 'n', 'r', 't', 'v'])
EscapeCharacter = SingleEscapeCharacter | '0' | 'x' | 'u'   # Changed DecimalDigit to 0 since it would match for example "\3" To verify..
NonEscapeCharacter = CharsNotIn([EscapeCharacter |LineTerminator])
CharacterEscapeSequence = SingleEscapeCharacter | NonEscapeCharacter
EscapeSequence = CharacterEscapeSequence | Combine('0'+NotAny(DecimalDigit)) | HexEscapeSequence | UnicodeEscapeSequence

SingleStringCharacter = CharsNotIn([LineTerminator | '\\' | "'"]) | Combine('\\'+EscapeSequence) | LineContinuation
DoubleStringCharacter = CharsNotIn([LineTerminator | '\\' | '"'])  | Combine('\\'+EscapeSequence) | LineContinuation
StringLiteral = Combine('"'+ZeroOrMore(DoubleStringCharacter)+'"') ^ Combine("'"+ZeroOrMore(SingleStringCharacter)+"'")

#Array


#Dict



                

