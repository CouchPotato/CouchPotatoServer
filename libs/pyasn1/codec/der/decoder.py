# DER decoder
from pyasn1.type import univ
from pyasn1.codec.cer import decoder

decode = decoder.Decoder(decoder.tagMap, decoder.typeMap)
