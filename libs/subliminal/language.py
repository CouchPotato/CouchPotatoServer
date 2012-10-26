# -*- coding: utf-8 -*-
# Copyright 2011-2012 Antoine Bertin <diaoulael@gmail.com>
#
# This file is part of subliminal.
#
# subliminal is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# subliminal is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with subliminal.  If not, see <http://www.gnu.org/licenses/>.
from .utils import to_unicode
import re
import logging


logger = logging.getLogger(__name__)


COUNTRIES = [('AF', 'AFG', '004', u'Afghanistan'),
             ('AX', 'ALA', '248', u'Åland Islands'),
             ('AL', 'ALB', '008', u'Albania'),
             ('DZ', 'DZA', '012', u'Algeria'),
             ('AS', 'ASM', '016', u'American Samoa'),
             ('AD', 'AND', '020', u'Andorra'),
             ('AO', 'AGO', '024', u'Angola'),
             ('AI', 'AIA', '660', u'Anguilla'),
             ('AQ', 'ATA', '010', u'Antarctica'),
             ('AG', 'ATG', '028', u'Antigua and Barbuda'),
             ('AR', 'ARG', '032', u'Argentina'),
             ('AM', 'ARM', '051', u'Armenia'),
             ('AW', 'ABW', '533', u'Aruba'),
             ('AU', 'AUS', '036', u'Australia'),
             ('AT', 'AUT', '040', u'Austria'),
             ('AZ', 'AZE', '031', u'Azerbaijan'),
             ('BS', 'BHS', '044', u'Bahamas'),
             ('BH', 'BHR', '048', u'Bahrain'),
             ('BD', 'BGD', '050', u'Bangladesh'),
             ('BB', 'BRB', '052', u'Barbados'),
             ('BY', 'BLR', '112', u'Belarus'),
             ('BE', 'BEL', '056', u'Belgium'),
             ('BZ', 'BLZ', '084', u'Belize'),
             ('BJ', 'BEN', '204', u'Benin'),
             ('BM', 'BMU', '060', u'Bermuda'),
             ('BT', 'BTN', '064', u'Bhutan'),
             ('BO', 'BOL', '068', u'Bolivia, Plurinational State of'),
             ('BQ', 'BES', '535', u'Bonaire, Sint Eustatius and Saba'),
             ('BA', 'BIH', '070', u'Bosnia and Herzegovina'),
             ('BW', 'BWA', '072', u'Botswana'),
             ('BV', 'BVT', '074', u'Bouvet Island'),
             ('BR', 'BRA', '076', u'Brazil'),
             ('IO', 'IOT', '086', u'British Indian Ocean Territory'),
             ('BN', 'BRN', '096', u'Brunei Darussalam'),
             ('BG', 'BGR', '100', u'Bulgaria'),
             ('BF', 'BFA', '854', u'Burkina Faso'),
             ('BI', 'BDI', '108', u'Burundi'),
             ('KH', 'KHM', '116', u'Cambodia'),
             ('CM', 'CMR', '120', u'Cameroon'),
             ('CA', 'CAN', '124', u'Canada'),
             ('CV', 'CPV', '132', u'Cape Verde'),
             ('KY', 'CYM', '136', u'Cayman Islands'),
             ('CF', 'CAF', '140', u'Central African Republic'),
             ('TD', 'TCD', '148', u'Chad'),
             ('CL', 'CHL', '152', u'Chile'),
             ('CN', 'CHN', '156', u'China'),
             ('CX', 'CXR', '162', u'Christmas Island'),
             ('CC', 'CCK', '166', u'Cocos (Keeling) Islands'),
             ('CO', 'COL', '170', u'Colombia'),
             ('KM', 'COM', '174', u'Comoros'),
             ('CG', 'COG', '178', u'Congo'),
             ('CD', 'COD', '180', u'Congo, The Democratic Republic of the'),
             ('CK', 'COK', '184', u'Cook Islands'),
             ('CR', 'CRI', '188', u'Costa Rica'),
             ('CI', 'CIV', '384', u'Côte d\'Ivoire'),
             ('HR', 'HRV', '191', u'Croatia'),
             ('CU', 'CUB', '192', u'Cuba'),
             ('CW', 'CUW', '531', u'Curaçao'),
             ('CY', 'CYP', '196', u'Cyprus'),
             ('CZ', 'CZE', '203', u'Czech Republic'),
             ('DK', 'DNK', '208', u'Denmark'),
             ('DJ', 'DJI', '262', u'Djibouti'),
             ('DM', 'DMA', '212', u'Dominica'),
             ('DO', 'DOM', '214', u'Dominican Republic'),
             ('EC', 'ECU', '218', u'Ecuador'),
             ('EG', 'EGY', '818', u'Egypt'),
             ('SV', 'SLV', '222', u'El Salvador'),
             ('GQ', 'GNQ', '226', u'Equatorial Guinea'),
             ('ER', 'ERI', '232', u'Eritrea'),
             ('EE', 'EST', '233', u'Estonia'),
             ('ET', 'ETH', '231', u'Ethiopia'),
             ('FK', 'FLK', '238', u'Falkland Islands (Malvinas)'),
             ('FO', 'FRO', '234', u'Faroe Islands'),
             ('FJ', 'FJI', '242', u'Fiji'),
             ('FI', 'FIN', '246', u'Finland'),
             ('FR', 'FRA', '250', u'France'),
             ('GF', 'GUF', '254', u'French Guiana'),
             ('PF', 'PYF', '258', u'French Polynesia'),
             ('TF', 'ATF', '260', u'French Southern Territories'),
             ('GA', 'GAB', '266', u'Gabon'),
             ('GM', 'GMB', '270', u'Gambia'),
             ('GE', 'GEO', '268', u'Georgia'),
             ('DE', 'DEU', '276', u'Germany'),
             ('GH', 'GHA', '288', u'Ghana'),
             ('GI', 'GIB', '292', u'Gibraltar'),
             ('GR', 'GRC', '300', u'Greece'),
             ('GL', 'GRL', '304', u'Greenland'),
             ('GD', 'GRD', '308', u'Grenada'),
             ('GP', 'GLP', '312', u'Guadeloupe'),
             ('GU', 'GUM', '316', u'Guam'),
             ('GT', 'GTM', '320', u'Guatemala'),
             ('GG', 'GGY', '831', u'Guernsey'),
             ('GN', 'GIN', '324', u'Guinea'),
             ('GW', 'GNB', '624', u'Guinea-Bissau'),
             ('GY', 'GUY', '328', u'Guyana'),
             ('HT', 'HTI', '332', u'Haiti'),
             ('HM', 'HMD', '334', u'Heard Island and McDonald Islands'),
             ('VA', 'VAT', '336', u'Holy See (Vatican City State)'),
             ('HN', 'HND', '340', u'Honduras'),
             ('HK', 'HKG', '344', u'Hong Kong'),
             ('HU', 'HUN', '348', u'Hungary'),
             ('IS', 'ISL', '352', u'Iceland'),
             ('IN', 'IND', '356', u'India'),
             ('ID', 'IDN', '360', u'Indonesia'),
             ('IR', 'IRN', '364', u'Iran, Islamic Republic of'),
             ('IQ', 'IRQ', '368', u'Iraq'),
             ('IE', 'IRL', '372', u'Ireland'),
             ('IM', 'IMN', '833', u'Isle of Man'),
             ('IL', 'ISR', '376', u'Israel'),
             ('IT', 'ITA', '380', u'Italy'),
             ('JM', 'JAM', '388', u'Jamaica'),
             ('JP', 'JPN', '392', u'Japan'),
             ('JE', 'JEY', '832', u'Jersey'),
             ('JO', 'JOR', '400', u'Jordan'),
             ('KZ', 'KAZ', '398', u'Kazakhstan'),
             ('KE', 'KEN', '404', u'Kenya'),
             ('KI', 'KIR', '296', u'Kiribati'),
             ('KP', 'PRK', '408', u'Korea, Democratic People\'s Republic of'),
             ('KR', 'KOR', '410', u'Korea, Republic of'),
             ('KW', 'KWT', '414', u'Kuwait'),
             ('KG', 'KGZ', '417', u'Kyrgyzstan'),
             ('LA', 'LAO', '418', u'Lao People\'s Democratic Republic'),
             ('LV', 'LVA', '428', u'Latvia'),
             ('LB', 'LBN', '422', u'Lebanon'),
             ('LS', 'LSO', '426', u'Lesotho'),
             ('LR', 'LBR', '430', u'Liberia'),
             ('LY', 'LBY', '434', u'Libya'),
             ('LI', 'LIE', '438', u'Liechtenstein'),
             ('LT', 'LTU', '440', u'Lithuania'),
             ('LU', 'LUX', '442', u'Luxembourg'),
             ('MO', 'MAC', '446', u'Macao'),
             ('MK', 'MKD', '807', u'Macedonia, Republic of'),
             ('MG', 'MDG', '450', u'Madagascar'),
             ('MW', 'MWI', '454', u'Malawi'),
             ('MY', 'MYS', '458', u'Malaysia'),
             ('MV', 'MDV', '462', u'Maldives'),
             ('ML', 'MLI', '466', u'Mali'),
             ('MT', 'MLT', '470', u'Malta'),
             ('MH', 'MHL', '584', u'Marshall Islands'),
             ('MQ', 'MTQ', '474', u'Martinique'),
             ('MR', 'MRT', '478', u'Mauritania'),
             ('MU', 'MUS', '480', u'Mauritius'),
             ('YT', 'MYT', '175', u'Mayotte'),
             ('MX', 'MEX', '484', u'Mexico'),
             ('FM', 'FSM', '583', u'Micronesia, Federated States of'),
             ('MD', 'MDA', '498', u'Moldova, Republic of'),
             ('MC', 'MCO', '492', u'Monaco'),
             ('MN', 'MNG', '496', u'Mongolia'),
             ('ME', 'MNE', '499', u'Montenegro'),
             ('MS', 'MSR', '500', u'Montserrat'),
             ('MA', 'MAR', '504', u'Morocco'),
             ('MZ', 'MOZ', '508', u'Mozambique'),
             ('MM', 'MMR', '104', u'Myanmar'),
             ('NA', 'NAM', '516', u'Namibia'),
             ('NR', 'NRU', '520', u'Nauru'),
             ('NP', 'NPL', '524', u'Nepal'),
             ('NL', 'NLD', '528', u'Netherlands'),
             ('NC', 'NCL', '540', u'New Caledonia'),
             ('NZ', 'NZL', '554', u'New Zealand'),
             ('NI', 'NIC', '558', u'Nicaragua'),
             ('NE', 'NER', '562', u'Niger'),
             ('NG', 'NGA', '566', u'Nigeria'),
             ('NU', 'NIU', '570', u'Niue'),
             ('NF', 'NFK', '574', u'Norfolk Island'),
             ('MP', 'MNP', '580', u'Northern Mariana Islands'),
             ('NO', 'NOR', '578', u'Norway'),
             ('OM', 'OMN', '512', u'Oman'),
             ('PK', 'PAK', '586', u'Pakistan'),
             ('PW', 'PLW', '585', u'Palau'),
             ('PS', 'PSE', '275', u'Palestinian Territory, Occupied'),
             ('PA', 'PAN', '591', u'Panama'),
             ('PG', 'PNG', '598', u'Papua New Guinea'),
             ('PY', 'PRY', '600', u'Paraguay'),
             ('PE', 'PER', '604', u'Peru'),
             ('PH', 'PHL', '608', u'Philippines'),
             ('PN', 'PCN', '612', u'Pitcairn'),
             ('PL', 'POL', '616', u'Poland'),
             ('PT', 'PRT', '620', u'Portugal'),
             ('PR', 'PRI', '630', u'Puerto Rico'),
             ('QA', 'QAT', '634', u'Qatar'),
             ('RE', 'REU', '638', u'Réunion'),
             ('RO', 'ROU', '642', u'Romania'),
             ('RU', 'RUS', '643', u'Russian Federation'),
             ('RW', 'RWA', '646', u'Rwanda'),
             ('BL', 'BLM', '652', u'Saint Barthélemy'),
             ('SH', 'SHN', '654', u'Saint Helena, Ascension and Tristan da Cunha'),
             ('KN', 'KNA', '659', u'Saint Kitts and Nevis'),
             ('LC', 'LCA', '662', u'Saint Lucia'),
             ('MF', 'MAF', '663', u'Saint Martin (French part)'),
             ('PM', 'SPM', '666', u'Saint Pierre and Miquelon'),
             ('VC', 'VCT', '670', u'Saint Vincent and the Grenadines'),
             ('WS', 'WSM', '882', u'Samoa'),
             ('SM', 'SMR', '674', u'San Marino'),
             ('ST', 'STP', '678', u'Sao Tome and Principe'),
             ('SA', 'SAU', '682', u'Saudi Arabia'),
             ('SN', 'SEN', '686', u'Senegal'),
             ('RS', 'SRB', '688', u'Serbia'),
             ('SC', 'SYC', '690', u'Seychelles'),
             ('SL', 'SLE', '694', u'Sierra Leone'),
             ('SG', 'SGP', '702', u'Singapore'),
             ('SX', 'SXM', '534', u'Sint Maarten (Dutch part)'),
             ('SK', 'SVK', '703', u'Slovakia'),
             ('SI', 'SVN', '705', u'Slovenia'),
             ('SB', 'SLB', '090', u'Solomon Islands'),
             ('SO', 'SOM', '706', u'Somalia'),
             ('ZA', 'ZAF', '710', u'South Africa'),
             ('GS', 'SGS', '239', u'South Georgia and the South Sandwich Islands'),
             ('ES', 'ESP', '724', u'Spain'),
             ('LK', 'LKA', '144', u'Sri Lanka'),
             ('SD', 'SDN', '729', u'Sudan'),
             ('SR', 'SUR', '740', u'Suriname'),
             ('SS', 'SSD', '728', u'South Sudan'),
             ('SJ', 'SJM', '744', u'Svalbard and Jan Mayen'),
             ('SZ', 'SWZ', '748', u'Swaziland'),
             ('SE', 'SWE', '752', u'Sweden'),
             ('CH', 'CHE', '756', u'Switzerland'),
             ('SY', 'SYR', '760', u'Syrian Arab Republic'),
             ('TW', 'TWN', '158', u'Taiwan, Province of China'),
             ('TJ', 'TJK', '762', u'Tajikistan'),
             ('TZ', 'TZA', '834', u'Tanzania, United Republic of'),
             ('TH', 'THA', '764', u'Thailand'),
             ('TL', 'TLS', '626', u'Timor-Leste'),
             ('TG', 'TGO', '768', u'Togo'),
             ('TK', 'TKL', '772', u'Tokelau'),
             ('TO', 'TON', '776', u'Tonga'),
             ('TT', 'TTO', '780', u'Trinidad and Tobago'),
             ('TN', 'TUN', '788', u'Tunisia'),
             ('TR', 'TUR', '792', u'Turkey'),
             ('TM', 'TKM', '795', u'Turkmenistan'),
             ('TC', 'TCA', '796', u'Turks and Caicos Islands'),
             ('TV', 'TUV', '798', u'Tuvalu'),
             ('UG', 'UGA', '800', u'Uganda'),
             ('UA', 'UKR', '804', u'Ukraine'),
             ('AE', 'ARE', '784', u'United Arab Emirates'),
             ('GB', 'GBR', '826', u'United Kingdom'),
             ('US', 'USA', '840', u'United States'),
             ('UM', 'UMI', '581', u'United States Minor Outlying Islands'),
             ('UY', 'URY', '858', u'Uruguay'),
             ('UZ', 'UZB', '860', u'Uzbekistan'),
             ('VU', 'VUT', '548', u'Vanuatu'),
             ('VE', 'VEN', '862', u'Venezuela, Bolivarian Republic of'),
             ('VN', 'VNM', '704', u'Viet Nam'),
             ('VG', 'VGB', '092', u'Virgin Islands, British'),
             ('VI', 'VIR', '850', u'Virgin Islands, U.S.'),
             ('WF', 'WLF', '876', u'Wallis and Futuna'),
             ('EH', 'ESH', '732', u'Western Sahara'),
             ('YE', 'YEM', '887', u'Yemen'),
             ('ZM', 'ZMB', '894', u'Zambia'),
             ('ZW', 'ZWE', '716', u'Zimbabwe')]


LANGUAGES = [('aar', '', 'aa', u'Afar', u'afar'),
             ('abk', '', 'ab', u'Abkhazian', u'abkhaze'),
             ('ace', '', '', u'Achinese', u'aceh'),
             ('ach', '', '', u'Acoli', u'acoli'),
             ('ada', '', '', u'Adangme', u'adangme'),
             ('ady', '', '', u'Adyghe; Adygei', u'adyghé'),
             ('afa', '', '', u'Afro-Asiatic languages', u'afro-asiatiques, langues'),
             ('afh', '', '', u'Afrihili', u'afrihili'),
             ('afr', '', 'af', u'Afrikaans', u'afrikaans'),
             ('ain', '', '', u'Ainu', u'aïnou'),
             ('aka', '', 'ak', u'Akan', u'akan'),
             ('akk', '', '', u'Akkadian', u'akkadien'),
             ('alb', 'sqi', 'sq', u'Albanian', u'albanais'),
             ('ale', '', '', u'Aleut', u'aléoute'),
             ('alg', '', '', u'Algonquian languages', u'algonquines, langues'),
             ('alt', '', '', u'Southern Altai', u'altai du Sud'),
             ('amh', '', 'am', u'Amharic', u'amharique'),
             ('ang', '', '', u'English, Old (ca.450-1100)', u'anglo-saxon (ca.450-1100)'),
             ('anp', '', '', u'Angika', u'angika'),
             ('apa', '', '', u'Apache languages', u'apaches, langues'),
             ('ara', '', 'ar', u'Arabic', u'arabe'),
             ('arc', '', '', u'Official Aramaic (700-300 BCE); Imperial Aramaic (700-300 BCE)', u'araméen d\'empire (700-300 BCE)'),
             ('arg', '', 'an', u'Aragonese', u'aragonais'),
             ('arm', 'hye', 'hy', u'Armenian', u'arménien'),
             ('arn', '', '', u'Mapudungun; Mapuche', u'mapudungun; mapuche; mapuce'),
             ('arp', '', '', u'Arapaho', u'arapaho'),
             ('art', '', '', u'Artificial languages', u'artificielles, langues'),
             ('arw', '', '', u'Arawak', u'arawak'),
             ('asm', '', 'as', u'Assamese', u'assamais'),
             ('ast', '', '', u'Asturian; Bable; Leonese; Asturleonese', u'asturien; bable; léonais; asturoléonais'),
             ('ath', '', '', u'Athapascan languages', u'athapascanes, langues'),
             ('aus', '', '', u'Australian languages', u'australiennes, langues'),
             ('ava', '', 'av', u'Avaric', u'avar'),
             ('ave', '', 'ae', u'Avestan', u'avestique'),
             ('awa', '', '', u'Awadhi', u'awadhi'),
             ('aym', '', 'ay', u'Aymara', u'aymara'),
             ('aze', '', 'az', u'Azerbaijani', u'azéri'),
             ('bad', '', '', u'Banda languages', u'banda, langues'),
             ('bai', '', '', u'Bamileke languages', u'bamiléké, langues'),
             ('bak', '', 'ba', u'Bashkir', u'bachkir'),
             ('bal', '', '', u'Baluchi', u'baloutchi'),
             ('bam', '', 'bm', u'Bambara', u'bambara'),
             ('ban', '', '', u'Balinese', u'balinais'),
             ('baq', 'eus', 'eu', u'Basque', u'basque'),
             ('bas', '', '', u'Basa', u'basa'),
             ('bat', '', '', u'Baltic languages', u'baltes, langues'),
             ('bej', '', '', u'Beja; Bedawiyet', u'bedja'),
             ('bel', '', 'be', u'Belarusian', u'biélorusse'),
             ('bem', '', '', u'Bemba', u'bemba'),
             ('ben', '', 'bn', u'Bengali', u'bengali'),
             ('ber', '', '', u'Berber languages', u'berbères, langues'),
             ('bho', '', '', u'Bhojpuri', u'bhojpuri'),
             ('bih', '', 'bh', u'Bihari languages', u'langues biharis'),
             ('bik', '', '', u'Bikol', u'bikol'),
             ('bin', '', '', u'Bini; Edo', u'bini; edo'),
             ('bis', '', 'bi', u'Bislama', u'bichlamar'),
             ('bla', '', '', u'Siksika', u'blackfoot'),
             ('bnt', '', '', u'Bantu (Other)', u'bantoues, autres langues'),
             ('bos', '', 'bs', u'Bosnian', u'bosniaque'),
             ('bra', '', '', u'Braj', u'braj'),
             ('bre', '', 'br', u'Breton', u'breton'),
             ('btk', '', '', u'Batak languages', u'batak, langues'),
             ('bua', '', '', u'Buriat', u'bouriate'),
             ('bug', '', '', u'Buginese', u'bugi'),
             ('bul', '', 'bg', u'Bulgarian', u'bulgare'),
             ('bur', 'mya', 'my', u'Burmese', u'birman'),
             ('byn', '', '', u'Blin; Bilin', u'blin; bilen'),
             ('cad', '', '', u'Caddo', u'caddo'),
             ('cai', '', '', u'Central American Indian languages', u'amérindiennes de L\'Amérique centrale, langues'),
             ('car', '', '', u'Galibi Carib', u'karib; galibi; carib'),
             ('cat', '', 'ca', u'Catalan; Valencian', u'catalan; valencien'),
             ('cau', '', '', u'Caucasian languages', u'caucasiennes, langues'),
             ('ceb', '', '', u'Cebuano', u'cebuano'),
             ('cel', '', '', u'Celtic languages', u'celtiques, langues; celtes, langues'),
             ('cha', '', 'ch', u'Chamorro', u'chamorro'),
             ('chb', '', '', u'Chibcha', u'chibcha'),
             ('che', '', 'ce', u'Chechen', u'tchétchène'),
             ('chg', '', '', u'Chagatai', u'djaghataï'),
             ('chi', 'zho', 'zh', u'Chinese', u'chinois'),
             ('chk', '', '', u'Chuukese', u'chuuk'),
             ('chm', '', '', u'Mari', u'mari'),
             ('chn', '', '', u'Chinook jargon', u'chinook, jargon'),
             ('cho', '', '', u'Choctaw', u'choctaw'),
             ('chp', '', '', u'Chipewyan; Dene Suline', u'chipewyan'),
             ('chr', '', '', u'Cherokee', u'cherokee'),
             ('chu', '', 'cu', u'Church Slavic; Old Slavonic; Church Slavonic; Old Bulgarian; Old Church Slavonic', u'slavon d\'église; vieux slave; slavon liturgique; vieux bulgare'),
             ('chv', '', 'cv', u'Chuvash', u'tchouvache'),
             ('chy', '', '', u'Cheyenne', u'cheyenne'),
             ('cmc', '', '', u'Chamic languages', u'chames, langues'),
             ('cop', '', '', u'Coptic', u'copte'),
             ('cor', '', 'kw', u'Cornish', u'cornique'),
             ('cos', '', 'co', u'Corsican', u'corse'),
             ('cpe', '', '', u'Creoles and pidgins, English based', u'créoles et pidgins basés sur l\'anglais'),
             ('cpf', '', '', u'Creoles and pidgins, French-based ', u'créoles et pidgins basés sur le français'),
             ('cpp', '', '', u'Creoles and pidgins, Portuguese-based ', u'créoles et pidgins basés sur le portugais'),
             ('cre', '', 'cr', u'Cree', u'cree'),
             ('crh', '', '', u'Crimean Tatar; Crimean Turkish', u'tatar de Crimé'),
             ('crp', '', '', u'Creoles and pidgins ', u'créoles et pidgins'),
             ('csb', '', '', u'Kashubian', u'kachoube'),
             ('cus', '', '', u'Cushitic languages', u'couchitiques, langues'),
             ('cze', 'ces', 'cs', u'Czech', u'tchèque'),
             ('dak', '', '', u'Dakota', u'dakota'),
             ('dan', '', 'da', u'Danish', u'danois'),
             ('dar', '', '', u'Dargwa', u'dargwa'),
             ('day', '', '', u'Land Dayak languages', u'dayak, langues'),
             ('del', '', '', u'Delaware', u'delaware'),
             ('den', '', '', u'Slave (Athapascan)', u'esclave (athapascan)'),
             ('dgr', '', '', u'Dogrib', u'dogrib'),
             ('din', '', '', u'Dinka', u'dinka'),
             ('div', '', 'dv', u'Divehi; Dhivehi; Maldivian', u'maldivien'),
             ('doi', '', '', u'Dogri', u'dogri'),
             ('dra', '', '', u'Dravidian languages', u'dravidiennes, langues'),
             ('dsb', '', '', u'Lower Sorbian', u'bas-sorabe'),
             ('dua', '', '', u'Duala', u'douala'),
             ('dum', '', '', u'Dutch, Middle (ca.1050-1350)', u'néerlandais moyen (ca. 1050-1350)'),
             ('dut', 'nld', 'nl', u'Dutch; Flemish', u'néerlandais; flamand'),
             ('dyu', '', '', u'Dyula', u'dioula'),
             ('dzo', '', 'dz', u'Dzongkha', u'dzongkha'),
             ('efi', '', '', u'Efik', u'efik'),
             ('egy', '', '', u'Egyptian (Ancient)', u'égyptien'),
             ('eka', '', '', u'Ekajuk', u'ekajuk'),
             ('elx', '', '', u'Elamite', u'élamite'),
             ('eng', '', 'en', u'English', u'anglais'),
             ('enm', '', '', u'English, Middle (1100-1500)', u'anglais moyen (1100-1500)'),
             ('epo', '', 'eo', u'Esperanto', u'espéranto'),
             ('est', '', 'et', u'Estonian', u'estonien'),
             ('ewe', '', 'ee', u'Ewe', u'éwé'),
             ('ewo', '', '', u'Ewondo', u'éwondo'),
             ('fan', '', '', u'Fang', u'fang'),
             ('fao', '', 'fo', u'Faroese', u'féroïen'),
             ('fat', '', '', u'Fanti', u'fanti'),
             ('fij', '', 'fj', u'Fijian', u'fidjien'),
             ('fil', '', '', u'Filipino; Pilipino', u'filipino; pilipino'),
             ('fin', '', 'fi', u'Finnish', u'finnois'),
             ('fiu', '', '', u'Finno-Ugrian languages', u'finno-ougriennes, langues'),
             ('fon', '', '', u'Fon', u'fon'),
             ('fre', 'fra', 'fr', u'French', u'français'),
             ('frm', '', '', u'French, Middle (ca.1400-1600)', u'français moyen (1400-1600)'),
             ('fro', '', '', u'French, Old (842-ca.1400)', u'français ancien (842-ca.1400)'),
             ('frr', '', '', u'Northern Frisian', u'frison septentrional'),
             ('frs', '', '', u'Eastern Frisian', u'frison oriental'),
             ('fry', '', 'fy', u'Western Frisian', u'frison occidental'),
             ('ful', '', 'ff', u'Fulah', u'peul'),
             ('fur', '', '', u'Friulian', u'frioulan'),
             ('gaa', '', '', u'Ga', u'ga'),
             ('gay', '', '', u'Gayo', u'gayo'),
             ('gba', '', '', u'Gbaya', u'gbaya'),
             ('gem', '', '', u'Germanic languages', u'germaniques, langues'),
             ('geo', 'kat', 'ka', u'Georgian', u'géorgien'),
             ('ger', 'deu', 'de', u'German', u'allemand'),
             ('gez', '', '', u'Geez', u'guèze'),
             ('gil', '', '', u'Gilbertese', u'kiribati'),
             ('gla', '', 'gd', u'Gaelic; Scottish Gaelic', u'gaélique; gaélique écossais'),
             ('gle', '', 'ga', u'Irish', u'irlandais'),
             ('glg', '', 'gl', u'Galician', u'galicien'),
             ('glv', '', 'gv', u'Manx', u'manx; mannois'),
             ('gmh', '', '', u'German, Middle High (ca.1050-1500)', u'allemand, moyen haut (ca. 1050-1500)'),
             ('goh', '', '', u'German, Old High (ca.750-1050)', u'allemand, vieux haut (ca. 750-1050)'),
             ('gon', '', '', u'Gondi', u'gond'),
             ('gor', '', '', u'Gorontalo', u'gorontalo'),
             ('got', '', '', u'Gothic', u'gothique'),
             ('grb', '', '', u'Grebo', u'grebo'),
             ('grc', '', '', u'Greek, Ancient (to 1453)', u'grec ancien (jusqu\'à 1453)'),
             ('gre', 'ell', 'el', u'Greek, Modern (1453-)', u'grec moderne (après 1453)'),
             ('grn', '', 'gn', u'Guarani', u'guarani'),
             ('gsw', '', '', u'Swiss German; Alemannic; Alsatian', u'suisse alémanique; alémanique; alsacien'),
             ('guj', '', 'gu', u'Gujarati', u'goudjrati'),
             ('gwi', '', '', u'Gwich\'in', u'gwich\'in'),
             ('hai', '', '', u'Haida', u'haida'),
             ('hat', '', 'ht', u'Haitian; Haitian Creole', u'haïtien; créole haïtien'),
             ('hau', '', 'ha', u'Hausa', u'haoussa'),
             ('haw', '', '', u'Hawaiian', u'hawaïen'),
             ('heb', '', 'he', u'Hebrew', u'hébreu'),
             ('her', '', 'hz', u'Herero', u'herero'),
             ('hil', '', '', u'Hiligaynon', u'hiligaynon'),
             ('him', '', '', u'Himachali languages; Western Pahari languages', u'langues himachalis; langues paharis occidentales'),
             ('hin', '', 'hi', u'Hindi', u'hindi'),
             ('hit', '', '', u'Hittite', u'hittite'),
             ('hmn', '', '', u'Hmong; Mong', u'hmong'),
             ('hmo', '', 'ho', u'Hiri Motu', u'hiri motu'),
             ('hrv', '', 'hr', u'Croatian', u'croate'),
             ('hsb', '', '', u'Upper Sorbian', u'haut-sorabe'),
             ('hun', '', 'hu', u'Hungarian', u'hongrois'),
             ('hup', '', '', u'Hupa', u'hupa'),
             ('iba', '', '', u'Iban', u'iban'),
             ('ibo', '', 'ig', u'Igbo', u'igbo'),
             ('ice', 'isl', 'is', u'Icelandic', u'islandais'),
             ('ido', '', 'io', u'Ido', u'ido'),
             ('iii', '', 'ii', u'Sichuan Yi; Nuosu', u'yi de Sichuan'),
             ('ijo', '', '', u'Ijo languages', u'ijo, langues'),
             ('iku', '', 'iu', u'Inuktitut', u'inuktitut'),
             ('ile', '', 'ie', u'Interlingue; Occidental', u'interlingue'),
             ('ilo', '', '', u'Iloko', u'ilocano'),
             ('ina', '', 'ia', u'Interlingua (International Auxiliary Language Association)', u'interlingua (langue auxiliaire internationale)'),
             ('inc', '', '', u'Indic languages', u'indo-aryennes, langues'),
             ('ind', '', 'id', u'Indonesian', u'indonésien'),
             ('ine', '', '', u'Indo-European languages', u'indo-européennes, langues'),
             ('inh', '', '', u'Ingush', u'ingouche'),
             ('ipk', '', 'ik', u'Inupiaq', u'inupiaq'),
             ('ira', '', '', u'Iranian languages', u'iraniennes, langues'),
             ('iro', '', '', u'Iroquoian languages', u'iroquoises, langues'),
             ('ita', '', 'it', u'Italian', u'italien'),
             ('jav', '', 'jv', u'Javanese', u'javanais'),
             ('jbo', '', '', u'Lojban', u'lojban'),
             ('jpn', '', 'ja', u'Japanese', u'japonais'),
             ('jpr', '', '', u'Judeo-Persian', u'judéo-persan'),
             ('jrb', '', '', u'Judeo-Arabic', u'judéo-arabe'),
             ('kaa', '', '', u'Kara-Kalpak', u'karakalpak'),
             ('kab', '', '', u'Kabyle', u'kabyle'),
             ('kac', '', '', u'Kachin; Jingpho', u'kachin; jingpho'),
             ('kal', '', 'kl', u'Kalaallisut; Greenlandic', u'groenlandais'),
             ('kam', '', '', u'Kamba', u'kamba'),
             ('kan', '', 'kn', u'Kannada', u'kannada'),
             ('kar', '', '', u'Karen languages', u'karen, langues'),
             ('kas', '', 'ks', u'Kashmiri', u'kashmiri'),
             ('kau', '', 'kr', u'Kanuri', u'kanouri'),
             ('kaw', '', '', u'Kawi', u'kawi'),
             ('kaz', '', 'kk', u'Kazakh', u'kazakh'),
             ('kbd', '', '', u'Kabardian', u'kabardien'),
             ('kha', '', '', u'Khasi', u'khasi'),
             ('khi', '', '', u'Khoisan languages', u'khoïsan, langues'),
             ('khm', '', 'km', u'Central Khmer', u'khmer central'),
             ('kho', '', '', u'Khotanese; Sakan', u'khotanais; sakan'),
             ('kik', '', 'ki', u'Kikuyu; Gikuyu', u'kikuyu'),
             ('kin', '', 'rw', u'Kinyarwanda', u'rwanda'),
             ('kir', '', 'ky', u'Kirghiz; Kyrgyz', u'kirghiz'),
             ('kmb', '', '', u'Kimbundu', u'kimbundu'),
             ('kok', '', '', u'Konkani', u'konkani'),
             ('kom', '', 'kv', u'Komi', u'kom'),
             ('kon', '', 'kg', u'Kongo', u'kongo'),
             ('kor', '', 'ko', u'Korean', u'coréen'),
             ('kos', '', '', u'Kosraean', u'kosrae'),
             ('kpe', '', '', u'Kpelle', u'kpellé'),
             ('krc', '', '', u'Karachay-Balkar', u'karatchai balkar'),
             ('krl', '', '', u'Karelian', u'carélien'),
             ('kro', '', '', u'Kru languages', u'krou, langues'),
             ('kru', '', '', u'Kurukh', u'kurukh'),
             ('kua', '', 'kj', u'Kuanyama; Kwanyama', u'kuanyama; kwanyama'),
             ('kum', '', '', u'Kumyk', u'koumyk'),
             ('kur', '', 'ku', u'Kurdish', u'kurde'),
             ('kut', '', '', u'Kutenai', u'kutenai'),
             ('lad', '', '', u'Ladino', u'judéo-espagnol'),
             ('lah', '', '', u'Lahnda', u'lahnda'),
             ('lam', '', '', u'Lamba', u'lamba'),
             ('lao', '', 'lo', u'Lao', u'lao'),
             ('lat', '', 'la', u'Latin', u'latin'),
             ('lav', '', 'lv', u'Latvian', u'letton'),
             ('lez', '', '', u'Lezghian', u'lezghien'),
             ('lim', '', 'li', u'Limburgan; Limburger; Limburgish', u'limbourgeois'),
             ('lin', '', 'ln', u'Lingala', u'lingala'),
             ('lit', '', 'lt', u'Lithuanian', u'lituanien'),
             ('lol', '', '', u'Mongo', u'mongo'),
             ('loz', '', '', u'Lozi', u'lozi'),
             ('ltz', '', 'lb', u'Luxembourgish; Letzeburgesch', u'luxembourgeois'),
             ('lua', '', '', u'Luba-Lulua', u'luba-lulua'),
             ('lub', '', 'lu', u'Luba-Katanga', u'luba-katanga'),
             ('lug', '', 'lg', u'Ganda', u'ganda'),
             ('lui', '', '', u'Luiseno', u'luiseno'),
             ('lun', '', '', u'Lunda', u'lunda'),
             ('luo', '', '', u'Luo (Kenya and Tanzania)', u'luo (Kenya et Tanzanie)'),
             ('lus', '', '', u'Lushai', u'lushai'),
             ('mac', 'mkd', 'mk', u'Macedonian', u'macédonien'),
             ('mad', '', '', u'Madurese', u'madourais'),
             ('mag', '', '', u'Magahi', u'magahi'),
             ('mah', '', 'mh', u'Marshallese', u'marshall'),
             ('mai', '', '', u'Maithili', u'maithili'),
             ('mak', '', '', u'Makasar', u'makassar'),
             ('mal', '', 'ml', u'Malayalam', u'malayalam'),
             ('man', '', '', u'Mandingo', u'mandingue'),
             ('mao', 'mri', 'mi', u'Maori', u'maori'),
             ('map', '', '', u'Austronesian languages', u'austronésiennes, langues'),
             ('mar', '', 'mr', u'Marathi', u'marathe'),
             ('mas', '', '', u'Masai', u'massaï'),
             ('may', 'msa', 'ms', u'Malay', u'malais'),
             ('mdf', '', '', u'Moksha', u'moksa'),
             ('mdr', '', '', u'Mandar', u'mandar'),
             ('men', '', '', u'Mende', u'mendé'),
             ('mga', '', '', u'Irish, Middle (900-1200)', u'irlandais moyen (900-1200)'),
             ('mic', '', '', u'Mi\'kmaq; Micmac', u'mi\'kmaq; micmac'),
             ('min', '', '', u'Minangkabau', u'minangkabau'),
             ('mkh', '', '', u'Mon-Khmer languages', u'môn-khmer, langues'),
             ('mlg', '', 'mg', u'Malagasy', u'malgache'),
             ('mlt', '', 'mt', u'Maltese', u'maltais'),
             ('mnc', '', '', u'Manchu', u'mandchou'),
             ('mni', '', '', u'Manipuri', u'manipuri'),
             ('mno', '', '', u'Manobo languages', u'manobo, langues'),
             ('moh', '', '', u'Mohawk', u'mohawk'),
             ('mon', '', 'mn', u'Mongolian', u'mongol'),
             ('mos', '', '', u'Mossi', u'moré'),
             ('mun', '', '', u'Munda languages', u'mounda, langues'),
             ('mus', '', '', u'Creek', u'muskogee'),
             ('mwl', '', '', u'Mirandese', u'mirandais'),
             ('mwr', '', '', u'Marwari', u'marvari'),
             ('myn', '', '', u'Mayan languages', u'maya, langues'),
             ('myv', '', '', u'Erzya', u'erza'),
             ('nah', '', '', u'Nahuatl languages', u'nahuatl, langues'),
             ('nai', '', '', u'North American Indian languages', u'nord-amérindiennes, langues'),
             ('nap', '', '', u'Neapolitan', u'napolitain'),
             ('nau', '', 'na', u'Nauru', u'nauruan'),
             ('nav', '', 'nv', u'Navajo; Navaho', u'navaho'),
             ('nbl', '', 'nr', u'Ndebele, South; South Ndebele', u'ndébélé du Sud'),
             ('nde', '', 'nd', u'Ndebele, North; North Ndebele', u'ndébélé du Nord'),
             ('ndo', '', 'ng', u'Ndonga', u'ndonga'),
             ('nds', '', '', u'Low German; Low Saxon; German, Low; Saxon, Low', u'bas allemand; bas saxon; allemand, bas; saxon, bas'),
             ('nep', '', 'ne', u'Nepali', u'népalais'),
             ('new', '', '', u'Nepal Bhasa; Newari', u'nepal bhasa; newari'),
             ('nia', '', '', u'Nias', u'nias'),
             ('nic', '', '', u'Niger-Kordofanian languages', u'nigéro-kordofaniennes, langues'),
             ('niu', '', '', u'Niuean', u'niué'),
             ('nno', '', 'nn', u'Norwegian Nynorsk; Nynorsk, Norwegian', u'norvégien nynorsk; nynorsk, norvégien'),
             ('nob', '', 'nb', u'Bokmål, Norwegian; Norwegian Bokmål', u'norvégien bokmål'),
             ('nog', '', '', u'Nogai', u'nogaï; nogay'),
             ('non', '', '', u'Norse, Old', u'norrois, vieux'),
             ('nor', '', 'no', u'Norwegian', u'norvégien'),
             ('nqo', '', '', u'N\'Ko', u'n\'ko'),
             ('nso', '', '', u'Pedi; Sepedi; Northern Sotho', u'pedi; sepedi; sotho du Nord'),
             ('nub', '', '', u'Nubian languages', u'nubiennes, langues'),
             ('nwc', '', '', u'Classical Newari; Old Newari; Classical Nepal Bhasa', u'newari classique'),
             ('nya', '', 'ny', u'Chichewa; Chewa; Nyanja', u'chichewa; chewa; nyanja'),
             ('nym', '', '', u'Nyamwezi', u'nyamwezi'),
             ('nyn', '', '', u'Nyankole', u'nyankolé'),
             ('nyo', '', '', u'Nyoro', u'nyoro'),
             ('nzi', '', '', u'Nzima', u'nzema'),
             ('oci', '', 'oc', u'Occitan (post 1500); Provençal', u'occitan (après 1500); provençal'),
             ('oji', '', 'oj', u'Ojibwa', u'ojibwa'),
             ('ori', '', 'or', u'Oriya', u'oriya'),
             ('orm', '', 'om', u'Oromo', u'galla'),
             ('osa', '', '', u'Osage', u'osage'),
             ('oss', '', 'os', u'Ossetian; Ossetic', u'ossète'),
             ('ota', '', '', u'Turkish, Ottoman (1500-1928)', u'turc ottoman (1500-1928)'),
             ('oto', '', '', u'Otomian languages', u'otomi, langues'),
             ('paa', '', '', u'Papuan languages', u'papoues, langues'),
             ('pag', '', '', u'Pangasinan', u'pangasinan'),
             ('pal', '', '', u'Pahlavi', u'pahlavi'),
             ('pam', '', '', u'Pampanga; Kapampangan', u'pampangan'),
             ('pan', '', 'pa', u'Panjabi; Punjabi', u'pendjabi'),
             ('pap', '', '', u'Papiamento', u'papiamento'),
             ('pau', '', '', u'Palauan', u'palau'),
             ('peo', '', '', u'Persian, Old (ca.600-400 B.C.)', u'perse, vieux (ca. 600-400 av. J.-C.)'),
             ('per', 'fas', 'fa', u'Persian', u'persan'),
             ('phi', '', '', u'Philippine languages', u'philippines, langues'),
             ('phn', '', '', u'Phoenician', u'phénicien'),
             ('pli', '', 'pi', u'Pali', u'pali'),
             ('pol', '', 'pl', u'Polish', u'polonais'),
             ('pon', '', '', u'Pohnpeian', u'pohnpei'),
             ('por', '', 'pt', u'Portuguese', u'portugais'),
             ('pra', '', '', u'Prakrit languages', u'prâkrit, langues'),
             ('pro', '', '', u'Provençal, Old (to 1500)', u'provençal ancien (jusqu\'à 1500)'),
             ('pus', '', 'ps', u'Pushto; Pashto', u'pachto'),
             ('que', '', 'qu', u'Quechua', u'quechua'),
             ('raj', '', '', u'Rajasthani', u'rajasthani'),
             ('rap', '', '', u'Rapanui', u'rapanui'),
             ('rar', '', '', u'Rarotongan; Cook Islands Maori', u'rarotonga; maori des îles Cook'),
             ('roa', '', '', u'Romance languages', u'romanes, langues'),
             ('roh', '', 'rm', u'Romansh', u'romanche'),
             ('rom', '', '', u'Romany', u'tsigane'),
             ('rum', 'ron', 'ro', u'Romanian; Moldavian; Moldovan', u'roumain; moldave'),
             ('run', '', 'rn', u'Rundi', u'rundi'),
             ('rup', '', '', u'Aromanian; Arumanian; Macedo-Romanian', u'aroumain; macédo-roumain'),
             ('rus', '', 'ru', u'Russian', u'russe'),
             ('sad', '', '', u'Sandawe', u'sandawe'),
             ('sag', '', 'sg', u'Sango', u'sango'),
             ('sah', '', '', u'Yakut', u'iakoute'),
             ('sai', '', '', u'South American Indian (Other)', u'indiennes d\'Amérique du Sud, autres langues'),
             ('sal', '', '', u'Salishan languages', u'salishennes, langues'),
             ('sam', '', '', u'Samaritan Aramaic', u'samaritain'),
             ('san', '', 'sa', u'Sanskrit', u'sanskrit'),
             ('sas', '', '', u'Sasak', u'sasak'),
             ('sat', '', '', u'Santali', u'santal'),
             ('scn', '', '', u'Sicilian', u'sicilien'),
             ('sco', '', '', u'Scots', u'écossais'),
             ('sel', '', '', u'Selkup', u'selkoupe'),
             ('sem', '', '', u'Semitic languages', u'sémitiques, langues'),
             ('sga', '', '', u'Irish, Old (to 900)', u'irlandais ancien (jusqu\'à 900)'),
             ('sgn', '', '', u'Sign Languages', u'langues des signes'),
             ('shn', '', '', u'Shan', u'chan'),
             ('sid', '', '', u'Sidamo', u'sidamo'),
             ('sin', '', 'si', u'Sinhala; Sinhalese', u'singhalais'),
             ('sio', '', '', u'Siouan languages', u'sioux, langues'),
             ('sit', '', '', u'Sino-Tibetan languages', u'sino-tibétaines, langues'),
             ('sla', '', '', u'Slavic languages', u'slaves, langues'),
             ('slo', 'slk', 'sk', u'Slovak', u'slovaque'),
             ('slv', '', 'sl', u'Slovenian', u'slovène'),
             ('sma', '', '', u'Southern Sami', u'sami du Sud'),
             ('sme', '', 'se', u'Northern Sami', u'sami du Nord'),
             ('smi', '', '', u'Sami languages', u'sames, langues'),
             ('smj', '', '', u'Lule Sami', u'sami de Lule'),
             ('smn', '', '', u'Inari Sami', u'sami d\'Inari'),
             ('smo', '', 'sm', u'Samoan', u'samoan'),
             ('sms', '', '', u'Skolt Sami', u'sami skolt'),
             ('sna', '', 'sn', u'Shona', u'shona'),
             ('snd', '', 'sd', u'Sindhi', u'sindhi'),
             ('snk', '', '', u'Soninke', u'soninké'),
             ('sog', '', '', u'Sogdian', u'sogdien'),
             ('som', '', 'so', u'Somali', u'somali'),
             ('son', '', '', u'Songhai languages', u'songhai, langues'),
             ('sot', '', 'st', u'Sotho, Southern', u'sotho du Sud'),
             ('spa', '', 'es', u'Spanish; Castilian', u'espagnol; castillan'),
             ('srd', '', 'sc', u'Sardinian', u'sarde'),
             ('srn', '', '', u'Sranan Tongo', u'sranan tongo'),
             ('srp', '', 'sr', u'Serbian', u'serbe'),
             ('srr', '', '', u'Serer', u'sérère'),
             ('ssa', '', '', u'Nilo-Saharan languages', u'nilo-sahariennes, langues'),
             ('ssw', '', 'ss', u'Swati', u'swati'),
             ('suk', '', '', u'Sukuma', u'sukuma'),
             ('sun', '', 'su', u'Sundanese', u'soundanais'),
             ('sus', '', '', u'Susu', u'soussou'),
             ('sux', '', '', u'Sumerian', u'sumérien'),
             ('swa', '', 'sw', u'Swahili', u'swahili'),
             ('swe', '', 'sv', u'Swedish', u'suédois'),
             ('syc', '', '', u'Classical Syriac', u'syriaque classique'),
             ('syr', '', '', u'Syriac', u'syriaque'),
             ('tah', '', 'ty', u'Tahitian', u'tahitien'),
             ('tai', '', '', u'Tai languages', u'tai, langues'),
             ('tam', '', 'ta', u'Tamil', u'tamoul'),
             ('tat', '', 'tt', u'Tatar', u'tatar'),
             ('tel', '', 'te', u'Telugu', u'télougou'),
             ('tem', '', '', u'Timne', u'temne'),
             ('ter', '', '', u'Tereno', u'tereno'),
             ('tet', '', '', u'Tetum', u'tetum'),
             ('tgk', '', 'tg', u'Tajik', u'tadjik'),
             ('tgl', '', 'tl', u'Tagalog', u'tagalog'),
             ('tha', '', 'th', u'Thai', u'thaï'),
             ('tib', 'bod', 'bo', u'Tibetan', u'tibétain'),
             ('tig', '', '', u'Tigre', u'tigré'),
             ('tir', '', 'ti', u'Tigrinya', u'tigrigna'),
             ('tiv', '', '', u'Tiv', u'tiv'),
             ('tkl', '', '', u'Tokelau', u'tokelau'),
             ('tlh', '', '', u'Klingon; tlhIngan-Hol', u'klingon'),
             ('tli', '', '', u'Tlingit', u'tlingit'),
             ('tmh', '', '', u'Tamashek', u'tamacheq'),
             ('tog', '', '', u'Tonga (Nyasa)', u'tonga (Nyasa)'),
             ('ton', '', 'to', u'Tonga (Tonga Islands)', u'tongan (Îles Tonga)'),
             ('tpi', '', '', u'Tok Pisin', u'tok pisin'),
             ('tsi', '', '', u'Tsimshian', u'tsimshian'),
             ('tsn', '', 'tn', u'Tswana', u'tswana'),
             ('tso', '', 'ts', u'Tsonga', u'tsonga'),
             ('tuk', '', 'tk', u'Turkmen', u'turkmène'),
             ('tum', '', '', u'Tumbuka', u'tumbuka'),
             ('tup', '', '', u'Tupi languages', u'tupi, langues'),
             ('tur', '', 'tr', u'Turkish', u'turc'),
             ('tut', '', '', u'Altaic languages', u'altaïques, langues'),
             ('tvl', '', '', u'Tuvalu', u'tuvalu'),
             ('twi', '', 'tw', u'Twi', u'twi'),
             ('tyv', '', '', u'Tuvinian', u'touva'),
             ('udm', '', '', u'Udmurt', u'oudmourte'),
             ('uga', '', '', u'Ugaritic', u'ougaritique'),
             ('uig', '', 'ug', u'Uighur; Uyghur', u'ouïgour'),
             ('ukr', '', 'uk', u'Ukrainian', u'ukrainien'),
             ('umb', '', '', u'Umbundu', u'umbundu'),
             ('und', '', '', u'Undetermined', u'indéterminée'),
             ('urd', '', 'ur', u'Urdu', u'ourdou'),
             ('uzb', '', 'uz', u'Uzbek', u'ouszbek'),
             ('vai', '', '', u'Vai', u'vaï'),
             ('ven', '', 've', u'Venda', u'venda'),
             ('vie', '', 'vi', u'Vietnamese', u'vietnamien'),
             ('vol', '', 'vo', u'Volapük', u'volapük'),
             ('vot', '', '', u'Votic', u'vote'),
             ('wak', '', '', u'Wakashan languages', u'wakashanes, langues'),
             ('wal', '', '', u'Walamo', u'walamo'),
             ('war', '', '', u'Waray', u'waray'),
             ('was', '', '', u'Washo', u'washo'),
             ('wel', 'cym', 'cy', u'Welsh', u'gallois'),
             ('wen', '', '', u'Sorbian languages', u'sorabes, langues'),
             ('wln', '', 'wa', u'Walloon', u'wallon'),
             ('wol', '', 'wo', u'Wolof', u'wolof'),
             ('xal', '', '', u'Kalmyk; Oirat', u'kalmouk; oïrat'),
             ('xho', '', 'xh', u'Xhosa', u'xhosa'),
             ('yao', '', '', u'Yao', u'yao'),
             ('yap', '', '', u'Yapese', u'yapois'),
             ('yid', '', 'yi', u'Yiddish', u'yiddish'),
             ('yor', '', 'yo', u'Yoruba', u'yoruba'),
             ('ypk', '', '', u'Yupik languages', u'yupik, langues'),
             ('zap', '', '', u'Zapotec', u'zapotèque'),
             ('zbl', '', '', u'Blissymbols; Blissymbolics; Bliss', u'symboles Bliss; Bliss'),
             ('zen', '', '', u'Zenaga', u'zenaga'),
             ('zha', '', 'za', u'Zhuang; Chuang', u'zhuang; chuang'),
             ('znd', '', '', u'Zande languages', u'zandé, langues'),
             ('zul', '', 'zu', u'Zulu', u'zoulou'),
             ('zun', '', '', u'Zuni', u'zuni'),
             ('zza', '', '', u'Zaza; Dimili; Dimli; Kirdki; Kirmanjki; Zazaki', u'zaza; dimili; dimli; kirdki; kirmanjki; zazaki')]


class Country(object):
    """Country according to ISO-3166

    :param string country: country name, alpha2 code, alpha3 code or numeric code
    :param list countries: all countries
    :type countries: see :data:`~subliminal.language.COUNTRIES`

    """
    def __init__(self, country, countries=None):
        countries = countries or COUNTRIES
        country = to_unicode(country.strip().lower())
        country_tuple = None

        # Try to find the country
        if len(country) == 2:
            country_tuple = dict((c[0].lower(), c) for c in countries).get(country)
        elif len(country) == 3 and not country.isdigit():
            country_tuple = dict((c[1].lower(), c) for c in countries).get(country)
        elif len(country) == 3 and country.isdigit():
            country_tuple = dict((c[2].lower(), c) for c in countries).get(country)
        if country_tuple is None:
            country_tuple = dict((c[3].lower(), c) for c in countries).get(country)

        # Raise ValueError if nothing is found
        if country_tuple is None:
            raise ValueError('Country %s does not exist' % country)

        # Set default attrs
        self.alpha2 = country_tuple[0]
        self.alpha3 = country_tuple[1]
        self.numeric = country_tuple[2]
        self.name = country_tuple[3]

    def __hash__(self):
        return hash(self.alpha3)

    def __eq__(self, other):
        if isinstance(other, Country):
            return self.alpha3 == other.alpha3
        return False

    def __ne__(self, other):
        return not self == other

    def __unicode__(self):
        return self.name

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        return 'Country(%s)' % self


class Language(object):
    """Language according to ISO-639

    :param string language: language name (english or french), alpha2 code, alpha3 code, terminologic code or numeric code, eventually with a country
    :param country: country of the language
    :type country: :class:`Country` or string
    :param languages: all languages
    :type languages: see :data:`~subliminal.language.LANGUAGES`
    :param countries: all countries
    :type countries: see :data:`~subliminal.language.COUNTRIES`
    :param bool strict: whether to raise a ValueError on unknown language or not

    :class:`Language` implements the inclusion test, with the ``in`` keyword::

        >>> Language('pt-BR') in Language('pt')  # Portuguese (Brazil) is included in Portuguese
        True
        >>> Language('pt') in Language('pt-BR')  # Portuguese is not included in Portuguese (Brazil)
        False

    """
    with_country_regexps = [re.compile('(.*)\((.*)\)'), re.compile('(.*)[-_](.*)')]

    def __init__(self, language, country=None, languages=None, countries=None, strict=True):
        languages = languages or LANGUAGES
        countries = countries or COUNTRIES

        # Get the country
        self.country = None
        if isinstance(country, Country):
            self.country = country
        elif isinstance(country, basestring):
            try:
                self.country = Country(country, countries)
            except ValueError:
                logger.warning(u'Country %s could not be identified' % country)
                if strict:
                    raise

        # Language + Country format
        #TODO: Improve this part
        if country is None:
            for regexp in [r.match(language) for r in self.with_country_regexps]:
                if regexp:
                    language = regexp.group(1)
                    try:
                        self.country = Country(regexp.group(2), countries)
                    except ValueError:
                        logger.warning(u'Country %s could not be identified' % country)
                        if strict:
                            raise
                    break

        # Try to find the language
        language = to_unicode(language.strip().lower())
        language_tuple = None
        if len(language) == 2:
            language_tuple = dict((l[2].lower(), l) for l in languages).get(language)
        elif len(language) == 3:
            language_tuple = dict((l[0].lower(), l) for l in languages).get(language)
            if language_tuple is None:
                language_tuple = dict((l[1].lower(), l) for l in languages).get(language)
        if language_tuple is None:
            language_tuple = dict((l[3].split('; ')[0].lower(), l) for l in languages).get(language)
        if language_tuple is None:
            language_tuple = dict((l[4].split('; ')[0].lower(), l) for l in languages).get(language)

        # Raise ValueError if strict or continue with Undetermined
        if language_tuple is None:
            if strict:
                raise ValueError('Language %s does not exist' % language)
            language_tuple = dict((l[0].lower(), l) for l in languages).get('und')

        # Set attributes
        self.alpha2 = language_tuple[2]
        self.alpha3 = language_tuple[0]
        self.terminologic = language_tuple[1]
        self.name = language_tuple[3]
        self.french_name = language_tuple[4]

    def __hash__(self):
        if self.country is None:
            return hash(self.alpha3)
        return hash(self.alpha3 + self.country.alpha3)

    def __eq__(self, other):
        if isinstance(other, Language):
            return self.alpha3 == other.alpha3 and self.country == other.country
        return False

    def __contains__(self, item):
        if isinstance(item, Language):
            if self == item:
                return True
            if self.country is None:
                return self.alpha3 == item.alpha3
        return False

    def __ne__(self, other):
        return not self == other

    def __nonzero__(self):
        return self.alpha3 != 'und'

    def __unicode__(self):
        if self.country is None:
            return self.name
        return '%s (%s)' % (self.name, self.country)

    def __str__(self):
        return unicode(self).encode('utf-8')

    def __repr__(self):
        if self.country is None:
            return 'Language(%s)' % self.name.encode('utf-8')
        return 'Language(%s, country=%s)' % (self.name.encode('utf-8'), self.country)


class language_set(set):
    """Set of :class:`Language` with some specificities.

    :param iterable: where to take elements from
    :type iterable: iterable of :class:`Languages <Language>` or string
    :param languages: all languages
    :type languages: see :data:`~subliminal.language.LANGUAGES`
    :param bool strict: whether to raise a ValueError on invalid language or not

    The following redefinitions are meant to reflect the inclusion logic in :class:`Language`

    * Inclusion test, with the ``in`` keyword
    * Intersection
    * Substraction

    Here is an illustration of the previous points::

        >>> Language('en') in language_set(['en-US', 'en-CA'])
        False
        >>> Language('en-US') in language_set(['en', 'fr'])
        True
        >>> language_set(['en']) & language_set(['en-US', 'en-CA'])
        language_set([Language(English, country=Canada), Language(English, country=United States)])
        >>> language_set(['en-US', 'en-CA', 'fr']) - language_set(['en'])
        language_set([Language(French)])

    """
    def __init__(self, iterable=None, languages=None, strict=True):
        iterable = iterable or []
        languages = languages or LANGUAGES
        items = []
        for i in iterable:
            if isinstance(i, Language):
                items.append(i)
                continue
            if isinstance(i, tuple):
                items.append(Language(i[0], languages=languages, strict=strict))
                continue
            items.append(Language(i, languages=languages, strict=strict))
        super(language_set, self).__init__(items)

    def __contains__(self, item):
        for i in self:
            if item in i:
                return True
        return super(language_set, self).__contains__(item)

    def __and__(self, other):
        results = language_set()
        for i in self:
            for j in other:
                if i in j:
                    results.add(i)
        for i in other:
            for j in self:
                if i in j:
                    results.add(i)
        return results

    def __sub__(self, other):
        results = language_set()
        for i in self:
            if i not in other:
                results.add(i)
        return results


class language_list(list):
    """List of :class:`Language` with some specificities.

    :param iterable: where to take elements from
    :type iterable: iterable of :class:`Languages <Language>` or string
    :param languages: all languages
    :type languages: see :data:`~subliminal.language.LANGUAGES`
    :param bool strict: whether to raise a ValueError on invalid language or not

    The following redefinitions are meant to reflect the inclusion logic in :class:`Language`

    * Inclusion test, with the ``in`` keyword
    * Index

    Here is an illustration of the previous points::

        >>> Language('en') in language_list(['en-US', 'en-CA'])
        False
        >>> Language('en-US') in language_list(['en', 'fr-BE'])
        True
        >>> language_list(['en', 'fr-BE']).index(Language('en-US'))
        0

    """
    def __init__(self, iterable=None, languages=None, strict=True):
        iterable = iterable or []
        languages = languages or LANGUAGES
        items = []
        for i in iterable:
            if isinstance(i, Language):
                items.append(i)
                continue
            if isinstance(i, tuple):
                items.append(Language(i[0], languages=languages, strict=strict))
                continue
            items.append(Language(i, languages=languages, strict=strict))
        super(language_list, self).__init__(items)

    def __contains__(self, item):
        for i in self:
            if item in i:
                return True
        return super(language_list, self).__contains__(item)

    def index(self, x, strict=False):
        if not strict:
            for i in range(len(self)):
                if x in self[i]:
                    return i
        return super(language_list, self).index(x)
