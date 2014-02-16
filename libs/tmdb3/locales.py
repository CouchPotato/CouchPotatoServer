#!/usr/bin/env python
# -*- coding: utf-8 -*-
#-----------------------
# Name: locales.py    Stores locale information for filtering results
# Python Library
# Author: Raymond Wagner
#-----------------------

from tmdb_exceptions import *
import locale

syslocale = None


class LocaleBase(object):
    __slots__ = ['__immutable']
    _stored = {}
    fallthrough = False

    def __init__(self, *keys):
        for key in keys:
            self._stored[key.lower()] = self
        self.__immutable = True

    def __setattr__(self, key, value):
        if getattr(self, '__immutable', False):
            raise NotImplementedError(self.__class__.__name__ +
                                      ' does not support modification.')
        super(LocaleBase, self).__setattr__(key, value)

    def __delattr__(self, key):
        if getattr(self, '__immutable', False):
            raise NotImplementedError(self.__class__.__name__ +
                                      ' does not support modification.')
        super(LocaleBase, self).__delattr__(key)

    def __lt__(self, other):
        return (id(self) != id(other)) and (str(self) > str(other))

    def __gt__(self, other):
        return (id(self) != id(other)) and (str(self) < str(other))

    def __eq__(self, other):
        return (id(self) == id(other)) or (str(self) == str(other))

    @classmethod
    def getstored(cls, key):
        if key is None:
            return None
        try:
            return cls._stored[key.lower()]
        except:
            raise TMDBLocaleError("'{0}' is not a known valid {1} code."\
                                  .format(key, cls.__name__))


class Language(LocaleBase):
    __slots__ = ['ISO639_1', 'ISO639_2', 'ISO639_2B', 'englishname',
                 'nativename']
    _stored = {}

    def __init__(self, iso1, iso2, ename):
        self.ISO639_1 = iso1
        self.ISO639_2 = iso2
#        self.ISO639_2B = iso2b
        self.englishname = ename
#        self.nativename = nname
        super(Language, self).__init__(iso1, iso2)

    def __str__(self):
        return self.ISO639_1

    def __repr__(self):
        return u"<Language '{0.englishname}' ({0.ISO639_1})>".format(self)


class Country(LocaleBase):
    __slots__ = ['alpha2', 'name']
    _stored = {}

    def __init__(self, alpha2, name):
        self.alpha2 = alpha2
        self.name = name
        super(Country, self).__init__(alpha2)

    def __str__(self):
        return self.alpha2

    def __repr__(self):
        return u"<Country '{0.name}' ({0.alpha2})>".format(self)


class Locale(LocaleBase):
    __slots__ = ['language', 'country', 'encoding']

    def __init__(self, language, country, encoding):
        self.language = Language.getstored(language)
        self.country = Country.getstored(country)
        self.encoding = encoding if encoding else 'latin-1'

    def __str__(self):
        return u"{0}_{1}".format(self.language, self.country)

    def __repr__(self):
        return u"<Locale {0.language}_{0.country}>".format(self)

    def encode(self, dat):
        """Encode using system default encoding for network/file output."""
        try:
            return dat.encode(self.encoding)
        except AttributeError:
            # not a string type, pass along
            return dat
        except UnicodeDecodeError:
            # just return unmodified and hope for the best
            return dat

    def decode(self, dat):
        """Decode to system default encoding for internal use."""
        try:
            return dat.decode(self.encoding)
        except AttributeError:
            # not a string type, pass along
            return dat
        except UnicodeEncodeError:
            # just return unmodified and hope for the best
            return dat


def set_locale(language=None, country=None, fallthrough=False):
    global syslocale
    LocaleBase.fallthrough = fallthrough

    sysloc, sysenc = locale.getdefaultlocale()

    if (not language) or (not country):
        dat = None
        if syslocale is not None:
            dat = (str(syslocale.language), str(syslocale.country))
        else:
            if (sysloc is None) or ('_' not in sysloc):
                dat = ('en', 'US')
            else:
                dat = sysloc.split('_')
        if language is None:
            language = dat[0]
        if country is None:
            country = dat[1]

    syslocale = Locale(language, country, sysenc)


def get_locale(language=-1, country=-1):
    """Output locale using provided attributes, or return system locale."""
    global syslocale
    # pull existing stored values
    if syslocale is None:
        loc = Locale(None, None, locale.getdefaultlocale()[1])
    else:
        loc = syslocale

    # both options are default, return stored values
    if language == country == -1:
        return loc

    # supplement default option with stored values
    if language == -1:
        language = loc.language
    elif country == -1:
        country = loc.country
    return Locale(language, country, loc.encoding)

######## AUTOGENERATED LANGUAGE AND COUNTRY DATA BELOW HERE #########

Language("ab", "abk", u"Abkhazian")
Language("aa", "aar", u"Afar")
Language("af", "afr", u"Afrikaans")
Language("ak", "aka", u"Akan")
Language("sq", "alb/sqi", u"Albanian")
Language("am", "amh", u"Amharic")
Language("ar", "ara", u"Arabic")
Language("an", "arg", u"Aragonese")
Language("hy", "arm/hye", u"Armenian")
Language("as", "asm", u"Assamese")
Language("av", "ava", u"Avaric")
Language("ae", "ave", u"Avestan")
Language("ay", "aym", u"Aymara")
Language("az", "aze", u"Azerbaijani")
Language("bm", "bam", u"Bambara")
Language("ba", "bak", u"Bashkir")
Language("eu", "baq/eus", u"Basque")
Language("be", "bel", u"Belarusian")
Language("bn", "ben", u"Bengali")
Language("bh", "bih", u"Bihari languages")
Language("bi", "bis", u"Bislama")
Language("nb", "nob", u"Bokmål, Norwegian")
Language("bs", "bos", u"Bosnian")
Language("br", "bre", u"Breton")
Language("bg", "bul", u"Bulgarian")
Language("my", "bur/mya", u"Burmese")
Language("es", "spa", u"Castilian")
Language("ca", "cat", u"Catalan")
Language("km", "khm", u"Central Khmer")
Language("ch", "cha", u"Chamorro")
Language("ce", "che", u"Chechen")
Language("ny", "nya", u"Chewa")
Language("ny", "nya", u"Chichewa")
Language("zh", "chi/zho", u"Chinese")
Language("za", "zha", u"Chuang")
Language("cu", "chu", u"Church Slavic")
Language("cu", "chu", u"Church Slavonic")
Language("cv", "chv", u"Chuvash")
Language("kw", "cor", u"Cornish")
Language("co", "cos", u"Corsican")
Language("cr", "cre", u"Cree")
Language("hr", "hrv", u"Croatian")
Language("cs", "cze/ces", u"Czech")
Language("da", "dan", u"Danish")
Language("dv", "div", u"Dhivehi")
Language("dv", "div", u"Divehi")
Language("nl", "dut/nld", u"Dutch")
Language("dz", "dzo", u"Dzongkha")
Language("en", "eng", u"English")
Language("eo", "epo", u"Esperanto")
Language("et", "est", u"Estonian")
Language("ee", "ewe", u"Ewe")
Language("fo", "fao", u"Faroese")
Language("fj", "fij", u"Fijian")
Language("fi", "fin", u"Finnish")
Language("nl", "dut/nld", u"Flemish")
Language("fr", "fre/fra", u"French")
Language("ff", "ful", u"Fulah")
Language("gd", "gla", u"Gaelic")
Language("gl", "glg", u"Galician")
Language("lg", "lug", u"Ganda")
Language("ka", "geo/kat", u"Georgian")
Language("de", "ger/deu", u"German")
Language("ki", "kik", u"Gikuyu")
Language("el", "gre/ell", u"Greek, Modern (1453-)")
Language("kl", "kal", u"Greenlandic")
Language("gn", "grn", u"Guarani")
Language("gu", "guj", u"Gujarati")
Language("ht", "hat", u"Haitian")
Language("ht", "hat", u"Haitian Creole")
Language("ha", "hau", u"Hausa")
Language("he", "heb", u"Hebrew")
Language("hz", "her", u"Herero")
Language("hi", "hin", u"Hindi")
Language("ho", "hmo", u"Hiri Motu")
Language("hu", "hun", u"Hungarian")
Language("is", "ice/isl", u"Icelandic")
Language("io", "ido", u"Ido")
Language("ig", "ibo", u"Igbo")
Language("id", "ind", u"Indonesian")
Language("ia", "ina", u"Interlingua (International Auxiliary Language Association)")
Language("ie", "ile", u"Interlingue")
Language("iu", "iku", u"Inuktitut")
Language("ik", "ipk", u"Inupiaq")
Language("ga", "gle", u"Irish")
Language("it", "ita", u"Italian")
Language("ja", "jpn", u"Japanese")
Language("jv", "jav", u"Javanese")
Language("kl", "kal", u"Kalaallisut")
Language("kn", "kan", u"Kannada")
Language("kr", "kau", u"Kanuri")
Language("ks", "kas", u"Kashmiri")
Language("kk", "kaz", u"Kazakh")
Language("ki", "kik", u"Kikuyu")
Language("rw", "kin", u"Kinyarwanda")
Language("ky", "kir", u"Kirghiz")
Language("kv", "kom", u"Komi")
Language("kg", "kon", u"Kongo")
Language("ko", "kor", u"Korean")
Language("kj", "kua", u"Kuanyama")
Language("ku", "kur", u"Kurdish")
Language("kj", "kua", u"Kwanyama")
Language("ky", "kir", u"Kyrgyz")
Language("lo", "lao", u"Lao")
Language("la", "lat", u"Latin")
Language("lv", "lav", u"Latvian")
Language("lb", "ltz", u"Letzeburgesch")
Language("li", "lim", u"Limburgan")
Language("li", "lim", u"Limburger")
Language("li", "lim", u"Limburgish")
Language("ln", "lin", u"Lingala")
Language("lt", "lit", u"Lithuanian")
Language("lu", "lub", u"Luba-Katanga")
Language("lb", "ltz", u"Luxembourgish")
Language("mk", "mac/mkd", u"Macedonian")
Language("mg", "mlg", u"Malagasy")
Language("ms", "may/msa", u"Malay")
Language("ml", "mal", u"Malayalam")
Language("dv", "div", u"Maldivian")
Language("mt", "mlt", u"Maltese")
Language("gv", "glv", u"Manx")
Language("mi", "mao/mri", u"Maori")
Language("mr", "mar", u"Marathi")
Language("mh", "mah", u"Marshallese")
Language("ro", "rum/ron", u"Moldavian")
Language("ro", "rum/ron", u"Moldovan")
Language("mn", "mon", u"Mongolian")
Language("na", "nau", u"Nauru")
Language("nv", "nav", u"Navaho")
Language("nv", "nav", u"Navajo")
Language("nd", "nde", u"Ndebele, North")
Language("nr", "nbl", u"Ndebele, South")
Language("ng", "ndo", u"Ndonga")
Language("ne", "nep", u"Nepali")
Language("nd", "nde", u"North Ndebele")
Language("se", "sme", u"Northern Sami")
Language("no", "nor", u"Norwegian")
Language("nb", "nob", u"Norwegian Bokmål")
Language("nn", "nno", u"Norwegian Nynorsk")
Language("ii", "iii", u"Nuosu")
Language("ny", "nya", u"Nyanja")
Language("nn", "nno", u"Nynorsk, Norwegian")
Language("ie", "ile", u"Occidental")
Language("oc", "oci", u"Occitan (post 1500)")
Language("oj", "oji", u"Ojibwa")
Language("cu", "chu", u"Old Bulgarian")
Language("cu", "chu", u"Old Church Slavonic")
Language("cu", "chu", u"Old Slavonic")
Language("or", "ori", u"Oriya")
Language("om", "orm", u"Oromo")
Language("os", "oss", u"Ossetian")
Language("os", "oss", u"Ossetic")
Language("pi", "pli", u"Pali")
Language("pa", "pan", u"Panjabi")
Language("ps", "pus", u"Pashto")
Language("fa", "per/fas", u"Persian")
Language("pl", "pol", u"Polish")
Language("pt", "por", u"Portuguese")
Language("pa", "pan", u"Punjabi")
Language("ps", "pus", u"Pushto")
Language("qu", "que", u"Quechua")
Language("ro", "rum/ron", u"Romanian")
Language("rm", "roh", u"Romansh")
Language("rn", "run", u"Rundi")
Language("ru", "rus", u"Russian")
Language("sm", "smo", u"Samoan")
Language("sg", "sag", u"Sango")
Language("sa", "san", u"Sanskrit")
Language("sc", "srd", u"Sardinian")
Language("gd", "gla", u"Scottish Gaelic")
Language("sr", "srp", u"Serbian")
Language("sn", "sna", u"Shona")
Language("ii", "iii", u"Sichuan Yi")
Language("sd", "snd", u"Sindhi")
Language("si", "sin", u"Sinhala")
Language("si", "sin", u"Sinhalese")
Language("sk", "slo/slk", u"Slovak")
Language("sl", "slv", u"Slovenian")
Language("so", "som", u"Somali")
Language("st", "sot", u"Sotho, Southern")
Language("nr", "nbl", u"South Ndebele")
Language("es", "spa", u"Spanish")
Language("su", "sun", u"Sundanese")
Language("sw", "swa", u"Swahili")
Language("ss", "ssw", u"Swati")
Language("sv", "swe", u"Swedish")
Language("tl", "tgl", u"Tagalog")
Language("ty", "tah", u"Tahitian")
Language("tg", "tgk", u"Tajik")
Language("ta", "tam", u"Tamil")
Language("tt", "tat", u"Tatar")
Language("te", "tel", u"Telugu")
Language("th", "tha", u"Thai")
Language("bo", "tib/bod", u"Tibetan")
Language("ti", "tir", u"Tigrinya")
Language("to", "ton", u"Tonga (Tonga Islands)")
Language("ts", "tso", u"Tsonga")
Language("tn", "tsn", u"Tswana")
Language("tr", "tur", u"Turkish")
Language("tk", "tuk", u"Turkmen")
Language("tw", "twi", u"Twi")
Language("ug", "uig", u"Uighur")
Language("uk", "ukr", u"Ukrainian")
Language("ur", "urd", u"Urdu")
Language("ug", "uig", u"Uyghur")
Language("uz", "uzb", u"Uzbek")
Language("ca", "cat", u"Valencian")
Language("ve", "ven", u"Venda")
Language("vi", "vie", u"Vietnamese")
Language("vo", "vol", u"Volapük")
Language("wa", "wln", u"Walloon")
Language("cy", "wel/cym", u"Welsh")
Language("fy", "fry", u"Western Frisian")
Language("wo", "wol", u"Wolof")
Language("xh", "xho", u"Xhosa")
Language("yi", "yid", u"Yiddish")
Language("yo", "yor", u"Yoruba")
Language("za", "zha", u"Zhuang")
Language("zu", "zul", u"Zulu")
Country("AF", u"AFGHANISTAN")
Country("AX", u"ÅLAND ISLANDS")
Country("AL", u"ALBANIA")
Country("DZ", u"ALGERIA")
Country("AS", u"AMERICAN SAMOA")
Country("AD", u"ANDORRA")
Country("AO", u"ANGOLA")
Country("AI", u"ANGUILLA")
Country("AQ", u"ANTARCTICA")
Country("AG", u"ANTIGUA AND BARBUDA")
Country("AR", u"ARGENTINA")
Country("AM", u"ARMENIA")
Country("AW", u"ARUBA")
Country("AU", u"AUSTRALIA")
Country("AT", u"AUSTRIA")
Country("AZ", u"AZERBAIJAN")
Country("BS", u"BAHAMAS")
Country("BH", u"BAHRAIN")
Country("BD", u"BANGLADESH")
Country("BB", u"BARBADOS")
Country("BY", u"BELARUS")
Country("BE", u"BELGIUM")
Country("BZ", u"BELIZE")
Country("BJ", u"BENIN")
Country("BM", u"BERMUDA")
Country("BT", u"BHUTAN")
Country("BO", u"BOLIVIA, PLURINATIONAL STATE OF")
Country("BQ", u"BONAIRE, SINT EUSTATIUS AND SABA")
Country("BA", u"BOSNIA AND HERZEGOVINA")
Country("BW", u"BOTSWANA")
Country("BV", u"BOUVET ISLAND")
Country("BR", u"BRAZIL")
Country("IO", u"BRITISH INDIAN OCEAN TERRITORY")
Country("BN", u"BRUNEI DARUSSALAM")
Country("BG", u"BULGARIA")
Country("BF", u"BURKINA FASO")
Country("BI", u"BURUNDI")
Country("KH", u"CAMBODIA")
Country("CM", u"CAMEROON")
Country("CA", u"CANADA")
Country("CV", u"CAPE VERDE")
Country("KY", u"CAYMAN ISLANDS")
Country("CF", u"CENTRAL AFRICAN REPUBLIC")
Country("TD", u"CHAD")
Country("CL", u"CHILE")
Country("CN", u"CHINA")
Country("CX", u"CHRISTMAS ISLAND")
Country("CC", u"COCOS (KEELING) ISLANDS")
Country("CO", u"COLOMBIA")
Country("KM", u"COMOROS")
Country("CG", u"CONGO")
Country("CD", u"CONGO, THE DEMOCRATIC REPUBLIC OF THE")
Country("CK", u"COOK ISLANDS")
Country("CR", u"COSTA RICA")
Country("CI", u"CÔTE D'IVOIRE")
Country("HR", u"CROATIA")
Country("CU", u"CUBA")
Country("CW", u"CURAÇAO")
Country("CY", u"CYPRUS")
Country("CZ", u"CZECH REPUBLIC")
Country("DK", u"DENMARK")
Country("DJ", u"DJIBOUTI")
Country("DM", u"DOMINICA")
Country("DO", u"DOMINICAN REPUBLIC")
Country("EC", u"ECUADOR")
Country("EG", u"EGYPT")
Country("SV", u"EL SALVADOR")
Country("GQ", u"EQUATORIAL GUINEA")
Country("ER", u"ERITREA")
Country("EE", u"ESTONIA")
Country("ET", u"ETHIOPIA")
Country("FK", u"FALKLAND ISLANDS (MALVINAS)")
Country("FO", u"FAROE ISLANDS")
Country("FJ", u"FIJI")
Country("FI", u"FINLAND")
Country("FR", u"FRANCE")
Country("GF", u"FRENCH GUIANA")
Country("PF", u"FRENCH POLYNESIA")
Country("TF", u"FRENCH SOUTHERN TERRITORIES")
Country("GA", u"GABON")
Country("GM", u"GAMBIA")
Country("GE", u"GEORGIA")
Country("DE", u"GERMANY")
Country("GH", u"GHANA")
Country("GI", u"GIBRALTAR")
Country("GR", u"GREECE")
Country("GL", u"GREENLAND")
Country("GD", u"GRENADA")
Country("GP", u"GUADELOUPE")
Country("GU", u"GUAM")
Country("GT", u"GUATEMALA")
Country("GG", u"GUERNSEY")
Country("GN", u"GUINEA")
Country("GW", u"GUINEA-BISSAU")
Country("GY", u"GUYANA")
Country("HT", u"HAITI")
Country("HM", u"HEARD ISLAND AND MCDONALD ISLANDS")
Country("VA", u"HOLY SEE (VATICAN CITY STATE)")
Country("HN", u"HONDURAS")
Country("HK", u"HONG KONG")
Country("HU", u"HUNGARY")
Country("IS", u"ICELAND")
Country("IN", u"INDIA")
Country("ID", u"INDONESIA")
Country("IR", u"IRAN, ISLAMIC REPUBLIC OF")
Country("IQ", u"IRAQ")
Country("IE", u"IRELAND")
Country("IM", u"ISLE OF MAN")
Country("IL", u"ISRAEL")
Country("IT", u"ITALY")
Country("JM", u"JAMAICA")
Country("JP", u"JAPAN")
Country("JE", u"JERSEY")
Country("JO", u"JORDAN")
Country("KZ", u"KAZAKHSTAN")
Country("KE", u"KENYA")
Country("KI", u"KIRIBATI")
Country("KP", u"KOREA, DEMOCRATIC PEOPLE'S REPUBLIC OF")
Country("KR", u"KOREA, REPUBLIC OF")
Country("KW", u"KUWAIT")
Country("KG", u"KYRGYZSTAN")
Country("LA", u"LAO PEOPLE'S DEMOCRATIC REPUBLIC")
Country("LV", u"LATVIA")
Country("LB", u"LEBANON")
Country("LS", u"LESOTHO")
Country("LR", u"LIBERIA")
Country("LY", u"LIBYA")
Country("LI", u"LIECHTENSTEIN")
Country("LT", u"LITHUANIA")
Country("LU", u"LUXEMBOURG")
Country("MO", u"MACAO")
Country("MK", u"MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF")
Country("MG", u"MADAGASCAR")
Country("MW", u"MALAWI")
Country("MY", u"MALAYSIA")
Country("MV", u"MALDIVES")
Country("ML", u"MALI")
Country("MT", u"MALTA")
Country("MH", u"MARSHALL ISLANDS")
Country("MQ", u"MARTINIQUE")
Country("MR", u"MAURITANIA")
Country("MU", u"MAURITIUS")
Country("YT", u"MAYOTTE")
Country("MX", u"MEXICO")
Country("FM", u"MICRONESIA, FEDERATED STATES OF")
Country("MD", u"MOLDOVA, REPUBLIC OF")
Country("MC", u"MONACO")
Country("MN", u"MONGOLIA")
Country("ME", u"MONTENEGRO")
Country("MS", u"MONTSERRAT")
Country("MA", u"MOROCCO")
Country("MZ", u"MOZAMBIQUE")
Country("MM", u"MYANMAR")
Country("NA", u"NAMIBIA")
Country("NR", u"NAURU")
Country("NP", u"NEPAL")
Country("NL", u"NETHERLANDS")
Country("NC", u"NEW CALEDONIA")
Country("NZ", u"NEW ZEALAND")
Country("NI", u"NICARAGUA")
Country("NE", u"NIGER")
Country("NG", u"NIGERIA")
Country("NU", u"NIUE")
Country("NF", u"NORFOLK ISLAND")
Country("MP", u"NORTHERN MARIANA ISLANDS")
Country("NO", u"NORWAY")
Country("OM", u"OMAN")
Country("PK", u"PAKISTAN")
Country("PW", u"PALAU")
Country("PS", u"PALESTINIAN TERRITORY, OCCUPIED")
Country("PA", u"PANAMA")
Country("PG", u"PAPUA NEW GUINEA")
Country("PY", u"PARAGUAY")
Country("PE", u"PERU")
Country("PH", u"PHILIPPINES")
Country("PN", u"PITCAIRN")
Country("PL", u"POLAND")
Country("PT", u"PORTUGAL")
Country("PR", u"PUERTO RICO")
Country("QA", u"QATAR")
Country("RE", u"RÉUNION")
Country("RO", u"ROMANIA")
Country("RU", u"RUSSIAN FEDERATION")
Country("RW", u"RWANDA")
Country("BL", u"SAINT BARTHÉLEMY")
Country("SH", u"SAINT HELENA, ASCENSION AND TRISTAN DA CUNHA")
Country("KN", u"SAINT KITTS AND NEVIS")
Country("LC", u"SAINT LUCIA")
Country("MF", u"SAINT MARTIN (FRENCH PART)")
Country("PM", u"SAINT PIERRE AND MIQUELON")
Country("VC", u"SAINT VINCENT AND THE GRENADINES")
Country("WS", u"SAMOA")
Country("SM", u"SAN MARINO")
Country("ST", u"SAO TOME AND PRINCIPE")
Country("SA", u"SAUDI ARABIA")
Country("SN", u"SENEGAL")
Country("RS", u"SERBIA")
Country("SC", u"SEYCHELLES")
Country("SL", u"SIERRA LEONE")
Country("SG", u"SINGAPORE")
Country("SX", u"SINT MAARTEN (DUTCH PART)")
Country("SK", u"SLOVAKIA")
Country("SI", u"SLOVENIA")
Country("SB", u"SOLOMON ISLANDS")
Country("SO", u"SOMALIA")
Country("ZA", u"SOUTH AFRICA")
Country("GS", u"SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS")
Country("SS", u"SOUTH SUDAN")
Country("ES", u"SPAIN")
Country("LK", u"SRI LANKA")
Country("SD", u"SUDAN")
Country("SR", u"SURINAME")
Country("SJ", u"SVALBARD AND JAN MAYEN")
Country("SZ", u"SWAZILAND")
Country("SE", u"SWEDEN")
Country("CH", u"SWITZERLAND")
Country("SY", u"SYRIAN ARAB REPUBLIC")
Country("TW", u"TAIWAN, PROVINCE OF CHINA")
Country("TJ", u"TAJIKISTAN")
Country("TZ", u"TANZANIA, UNITED REPUBLIC OF")
Country("TH", u"THAILAND")
Country("TL", u"TIMOR-LESTE")
Country("TG", u"TOGO")
Country("TK", u"TOKELAU")
Country("TO", u"TONGA")
Country("TT", u"TRINIDAD AND TOBAGO")
Country("TN", u"TUNISIA")
Country("TR", u"TURKEY")
Country("TM", u"TURKMENISTAN")
Country("TC", u"TURKS AND CAICOS ISLANDS")
Country("TV", u"TUVALU")
Country("UG", u"UGANDA")
Country("UA", u"UKRAINE")
Country("AE", u"UNITED ARAB EMIRATES")
Country("GB", u"UNITED KINGDOM")
Country("US", u"UNITED STATES")
Country("UM", u"UNITED STATES MINOR OUTLYING ISLANDS")
Country("UY", u"URUGUAY")
Country("UZ", u"UZBEKISTAN")
Country("VU", u"VANUATU")
Country("VE", u"VENEZUELA, BOLIVARIAN REPUBLIC OF")
Country("VN", u"VIET NAM")
Country("VG", u"VIRGIN ISLANDS, BRITISH")
Country("VI", u"VIRGIN ISLANDS, U.S.")
Country("WF", u"WALLIS AND FUTUNA")
Country("EH", u"WESTERN SAHARA")
Country("YE", u"YEMEN")
Country("ZM", u"ZAMBIA")
Country("ZW", u"ZIMBABWE")
