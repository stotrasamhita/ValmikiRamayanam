#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
from transliterator import transliterate as tr

# def _tr(text):
#     return tr(text, 'harvardkyoto', 'devanagari')

kANDa = {1: 'bAla',
         2: 'ayOdhyA',
         3: 'araNya',
         4: 'kiSkindhA',
         5: 'sundara',
         6: 'yuddha',
         7: 'uttara'}

sarga = {1: "prathamaH",
         2: "dwitIyaH",
         3: "tRtIyaH",
         4: "caturthaH",
         5: "paJcamaH",
         6: "SaSThaH",
         7: "saptamaH",
         8: "aSTamaH",
         9: "navamaH",
         10: "dazamaH",
         11: "EkAdazaH",
         12: "dwAdazaH",
         13: "trayOdazaH",
         14: "caturdazaH",
         15: "paJcadazaH",
         16: "SODazaH",
         17: "saptadazaH",
         18: "aSTAdazaH",
         19: "EkOnaviMzaH",
         20: "viMzaH",
         21: "EkaviMzaH",
         22: "dwAviMzaH",
         23: "trayOviMzaH",
         24: "caturviMzaH",
         25: "paJcaviMzaH",
         26: "SaDviMzaH",
         27: "saptaviMzaH",
         28: "aSTAviMzaH",
         29: "EkOnatriMzaH",
         30: "triMzaH",
         31: "EkatriMzaH",
         32: "dwAtriMzaH",
         33: "trayastriMzaH",
         34: "catustriMzaH",
         35: "paJcatriMzaH",
         36: "SaTtriMzaH",
         37: "saptatriMzaH",
         38: "aSTAtriMzaH",
         39: "EkOnacatvAriMzaH",
         40: "catvAriMzaH",
         41: "EkacatvAriMzaH",
         42: "dwicatvAriMzaH",
         43: "tricatvAriMzaH",
         44: "catuzcatvAriMzaH",
         45: "paJcacatvAriMzaH",
         46: "SaTcatvAriMzaH",
         47: "saptacatvAriMzaH",
         48: "aSTacatvAriMzaH",
         49: "EkOnapaJcAzattamaH",
         50: "paJcAzattamaH",
         51: "EkapaJcAzattamaH",
         52: "dwipaJcAzattamaH",
         53: "tripaJcAzattamaH",
         54: "catuHpaJcAzattamaH",
         55: "paJcapaJcAzattamaH",
         56: "SaTpaJcAzattamaH",
         57: "saptapaJcAzattamaH",
         58: "aSTapaJcAzattamaH",
         59: "EkOnaSaSTitamaH",
         60: "SaSTitamaH",
         61: "EkaSaSTitamaH",
         62: "dwiSaSTitamaH",
         63: "triSaSTitamaH",
         64: "catuHSaSTitamaH",
         65: "paJcaSaSTitamaH",
         66: "SaTSaSTitamaH",
         67: "saptaSaSTitamaH",
         68: "aSTaSaSTitamaH",
         69: "EkOnasaptatitamaH",
         70: "saptatitamaH",
         71: "EkasaptatitamaH",
         72: "dwisaptatitamaH",
         73: "trisaptatitamaH",
         74: "catuHsaptatitamaH",
         75: "paJcasaptatitamaH",
         76: "SaTsaptatitamaH",
         77: "saptasaptatitamaH",
         78: "aSTasaptatitamaH",
         79: "EkOnAzItitamaH",
         80: "azItitamaH",
         81: "EkAzItitamaH",
         82: "dvyazItitamaH",
         83: "tryazItitamaH",
         84: "caturazItitamaH",
         85: "paJcAzItitamaH",
         86: "SaDazItitamaH",
         87: "saptAzItitamaH",
         88: "aSTAzItitamaH",
         89: "EkOnanavatitamaH",
         90: "navatitamaH",
         91: "ekanavatitamaH",
         92: "dvinavatitamaH",
         93: "trinavatitamaH",
         94: "caturnavatitamaH",
         95: "paJcanavatitamaH",
         96: "SaNNavatitamaH",
         97: "saptanavatitamaH",
         98: "aSTanavatitamaH",
         99: "EkonazatatamaH",
         100: "zatatamaH",
         101: "ekAdhikazatatamaH",
         102: "dvyadhikazatatamaH",
         103: "tryadhikazatatamaH",
         104: "caturadhikazatatamaH",
         105: "paJcAdhikazatatamaH",
         106: "SaSThAdhikazatatamaH",
         107: "saptamAdhikazatatamaH",
         108: "aSTamAdhikazatatamaH",
         109: "navamAdhikazatatamaH",
         110: "dazamAdhikazatatamaH",
         111: "EkAdazAdhikazatatamaH",
         112: "dwAdazAdhikazatatamaH",
         113: "trayOdazAdhikazatatamaH",
         114: "caturdazAdhikazatatamaH",
         115: "paJcadazAdhikazatatamaH",
         116: "SODazAdhikazatatamaH"}

chapter_file = open(sys.argv[1])
chapter_lines = chapter_file.readlines()
nSargas = int(chapter_lines[-1][1:4])
chapter_lines.append('%d%03d001a iti\n1%03d001c iti' %
                     (int(chapter_lines[-1][0]), nSargas + 1, nSargas + 1))
# Poor coding, to assist the while loop to read the last verse!

num_chapter_lines = len(chapter_lines)

# print("{{Ramayanam}}")

for i in range(num_chapter_lines):
    line1 = chapter_lines[i]
    if line1.find('%') != -1:
        # Skip comment line!
        continue
    nLines = 0
    isProse = 0

    shloka_ID = line1[:8]
    shloka_text = line1[9:]
    kandanum = int(shloka_ID[0])
    sarganum = int(shloka_ID[1:4])
    shlokanum = int(shloka_ID[4:7])
    currShloka = shlokanum
    currSarga = sarganum
    pada = shloka_ID[-1]
    # print(i, shloka_ID, shloka_text, kandanum, sarganum, shlokanum)

    if sarganum > 1 and shlokanum == 1 and pada == 'a':
        iti_text = tr('ityArSe zrImadrAmAyaNe vAlmIkIyE AdikAvyE %skANDE %s sargaH'
                      % (kANDa[kandanum], sarga[sarganum - 1]), 'harvardkyoto', 'devanagari')
        print('\n{॥%s॥}\n' % iti_text)

    if sarganum == nSargas + 1:
        exit(0)

    if sarganum == 1 and shlokanum == 1 and pada == 'a':
        print('\\chapt{%s}\n' % tr(kANDa[kandanum] + 'kANDaH', 'harvardkyoto', 'devanagari'))

    if shlokanum == 1 and pada == 'a':
        print('\\sect{%s}\n' % tr(sarga[sarganum] + ' sargaH', 'harvardkyoto', 'devanagari'))

    # if shlokanum == 0:
    #     print('<lipi><b>%s</b></lipi>' % (shloka_text))
    #     continue

    if pada == 'a':
        shloka_lines = [None] * 5
        shloka_num = int(shloka_ID[4:7])

        while shlokanum == currShloka:
            shloka_lines[nLines] = shloka_text

            if (i + 1) >= num_chapter_lines:
                iti_text = tr('ityArSe zrImadrAmAyaNe vAlmIkIyE AdikAvyE %skANDE %s sargaH'
                              % (kANDa[kandanum], sarga[sarganum]), 'harvardkyoto', 'devanagari')
                print('\n{॥%s॥}\n' % iti_text)
                exit(0)
            else:
                nextline = chapter_lines[i + 1]

                shloka_ID = nextline[:8]
                shloka_text = nextline[9:]
                # kandanum = int(shloka_ID[0])
                sarganum = int(shloka_ID[1:4])
                shlokanum = int(shloka_ID[4:7])

                nLines += 1
                i += 1

        # if nLines != 2:
        # print(nLines, '!!')

        if nLines == 2:
            if shloka_lines[0].find(';') == -1:
                print('\\twolineshloka')
                print('{%s}\n{%s} %%||%d-%d-%d||\n' % (shloka_lines[0][:-1],
                      shloka_lines[1][:-1], kandanum, sarganum, shloka_num))
            else:
                print('\\fourlineindentedshloka')
                [l1, l2] = shloka_lines[0][:-1].split(';')
                [l3, l4] = shloka_lines[1][:-1].split(';')
                print('{%s}\n{%s}\n{%s}\n{%s} %%||%d-%d-%d||\n' %
                      (l1, l2, l3, l4, kandanum, sarganum, shloka_num))

        elif nLines == 1:
            print('{%s॥\devanumber{%d}॥} %%||%d-%d-%d|| (Check)\n' % (shloka_lines[0][:-1],
                  shloka_num, kandanum, sarganum, shloka_num))
            print('\\addtocounter{shlokacount}{1}\n')

        elif nLines == 3:
            print('\\threelineshloka')
            print('{%s}\n{%s}\n{%s} %%||%d-%d-%d||\n' % (shloka_lines[0][:-1],
                  shloka_lines[1][:-1], shloka_lines[2][:-1], kandanum, sarganum, shloka_num))

        elif nLines == 4:
            print('\\fourlineshloka')
            print('{%s}\n{%s}\n{%s}\n{%s} %%||%d-%d-%d||\n' % (shloka_lines[0][:-1],
                  shloka_lines[1][:-1],
                  shloka_lines[2][:-1], shloka_lines[3][:-1], kandanum, sarganum, shloka_num))

        else:
            print('Warning! Unknown line style!! nLines = %d!' % nLines)
