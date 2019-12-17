# Python 3.1
from operator import itemgetter
import csv
import os.path
from zipfile import *
import copy 
import re
from chardet.universaldetector import UniversalDetector
from collections import Counter

tokpatt = "([\w][\w\d-]*)([\w][\w]*'ll)|([\w][\w]*'ve)|(it's)|([\w][\w]*'t)|([\w][\w]*'d)|(where's)|(what's)|(she's)|(he's)|([\w][\w]*'re)|(i'm)|(that's)|(let's)|([\w][\w\d-]*)"

def mungleWord(word):
    if word[0:1] == "'":
        word = word[1:]
    return word.replace('^',"'").strip()

class LDictText:
    """Text to be analysed for word usage"""
    def __init__(self, fileName):
        self.fileName = fileName
        self.detector = UniversalDetector()
    def getWords(self):
        """Returns iterator on words in text"""
        self.detector.reset()
        for line in open(self.fileName, 'rb'):
            self.detector.feed(line)
            if self.detector.done: break
        self.detector.close()
        inFile = open(self.fileName,'r',encoding=self.detector.result['encoding'],errors='replace')
#        patt = "[\p{L}][\p{L}\p{Nd}-]*"
        t = inFile.read()
#        print(t[1:150])
        inFile.close()
        return(re.finditer(tokpatt,t,flags=re.I))

class LDictCountReport:
    """Holds categorycounts and word frequencies by category"""
    def __init__(self, catList):
        """Creates dictionary holding category counts and dict holding word frequencies"""
        self.catCount = dict.fromkeys(catList,0)
        self.catWordCount = {k:{} for k in catList}
        self.catList = catList
    def addWord(self, word,catList,count=1):
        """increases counters for word in cats"""
        for cat in catList:
            self.catCount[cat] += count
            if word in self.catWordCount[cat]:
                self.catWordCount[cat][word] += count
            else:
                self.catWordCount[cat][word] = count
    def write(self,zipout,fq='',freq=0.015):
#        print(self)
        """Writes frequencies to zipfile"""
        zipf = ZipFile(zipout,'w')
        kop = 'word;freq;relfreq\n'
        for cat in self.catList:
            if fq != '':
                outfile = cat + '.' + fq + '.csv'
            else:
                outfile = cat + '.csv'
            txt = kop
            sumf = sum(self.catWordCount[cat].values()) 
            for w in sorted(self.catWordCount[cat].keys()):
                c = self.catWordCount[cat][w]
#                print(c,sumf,freq,c/sumf > freq)
                if c/sumf > freq:
                    txt += w
                    txt += ';' + str(c)
                    txt += ';' + str(100*c/sumf).replace('.',',')
                    txt += '\n'
            zipf.writestr(outfile,txt)
        outfile = 'all' + '.' + fq + '.csv'
        txt = 'word;freq\n'
        for cat in self.catList:
            txt += cat + ';' + str(self.catCount[cat])+ '\n'
        zipf.writestr(outfile,txt)
        zipf.close()

class LDictUpdateReport:
    """LIWC dictionary update report"""
    def __init__(self, updateFile,dictFile):
        """Create a LIWC Dictionary update file report"""
        self.updateFile = updateFile
        self.dictFile = dictFile
        self.cats = []
        self.mode = ''
        self.updatetype = ''
        self.counts = {'#donebefore':0,'#reject':0,'#noequiv':0,'#hulpww':0,'splitwords':0,
                       'addition':0,'#add':0,'#remove':0,'removes':0}
    def LDictURPrint(self):
        print('Report of dictionary update')
        print('updateFile',self.updateFile)
        print('dictFile',self.dictFile)
        print('updatetype',self.updatetype)
        print('cats',self.cats)
        print('mode',self.mode)
        print('counts',self.counts,'\n')
    def addCat(self,cat):
        self.counts[cat] += 1
    
class LDictMatch:
    """LIWC dictionary matcher"""
    
    def __init__(self, fileName):
        """Create a LIWC Dictionary match object
        Reads the dictionary matching file and sets up three python dictionaries:
        dictOld, which maps old categories to a list of new ones or 'none'
        dictNew, which maps new categories to a list of old ones or 'none'
        dictNewLabel, which maps a new category to its label
        The old labels are ignored
        """
        self.fileName = fileName
        f = open(fileName, newline='')
        csvReader = csv.reader(f, delimiter=';',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        self.dictOld = {}
        self.dictNew = {}
        self.dictNewLabel = {}
        firstRow = True
        for row in csvReader:
            if firstRow:
                firstRow = False
                self.labelOld = row[0]
                self.labelNew = row[2]
                continue 
            if row[0] == '': # new category
                self.dictNew[row[2]] = 'none'
                self.dictNewLabel[row[2]] = row[3]
            elif row[2] == '': # old cat, no corresponding new cat
                self.dictOld[row[0]] = 'none'
            else:
                self.dictNewLabel[row[2]] = row[3]
                if row[0] in self.dictOld: 
                    self.dictOld[row[0]].append(row[2])
                else:
                    self.dictOld[row[0]] = [row[2]]
                if row[2] in self.dictNew: 
                    self.dictNew[row[2]].append(row[0])
                else:
                    self.dictNew[row[2]] = [row[0]]
        f.close()
    def addCat(self,cat,label):
        """
        Adds new category to the matcher
        """
        self.dictNewLabel[str(int(cat))] = label
        self.dictNew[str(int(cat))] = 'none'
    def convertDict(self,LDold):
        """Convert an existing LIWC dictionary to a new one
        
        Takes one variable: an existing LIWC dictionary .  
        The existing LIWC dictionary is converted to a new one based on the
        dictionary matcher's mappings.
        Takes all words in old cat, not just extrahierarchical words
        """ 
        LDnew = LDict('')
        for c in self.dictNew: # add empty cats with labels
            LDnew.catDict.addCat(c,self.dictNewLabel[c],set())
        for c in LDold.catDict.catDict: # for each cat in old dict
            if self.dictOld[c] != 'none': # if it has couterpart in new dict
                LDnew.wordSet = LDnew.wordSet | LDold.catDict.catDict[c][1] # add words to dict
                for ct in self.dictOld[c]:                      # for each counterpart cat, add cat words to counterpart cat
                    LDnew.catDict.addWordSet(ct,LDold.catDict.catDict[c][1])
        return LDnew
    
    def LPrint(self):
        """Print the Dictionary matcher to stdout"""
        print('fileName',self.fileName)
        print('labels',self.labelOld,self.labelNew)
        print('dictOld',self.dictOld)
        print('dictNew',self.dictNew)
        
    def HtmlView(self,outFile,LDold,LDnew):
        html = '<html>\n<head><style type="text/css">\n \
               *{font-family: Arial,Verdana;}\
               td{width:20%;vertical-align:top}\
               table,td{border: 1px solid black;}\
               .noehw{color:grey}\
               .match{background-color:#ffff99}\
                </style><title>Compare'
        html += self.fileName
        html += '</title>\n</head>\n<body>\n<a name="top"/><h1>Compare  LIWC dictionaries</h1>\n<p><b>Matching file:</b> '
        html += self.fileName
        html += '<br/>\n<b>Old dict:</b> '
        html += LDold.fileName
        html += ',number of words: '
        html += str(len(LDold.wordSet))
        html += '<br/><b>New dict:</b> '
        html += LDnew.fileName
        html += ',number of words: '
        html += str(len(LDnew.wordSet))
        html += '</p>\n<p>Unhandled lines old dict:<br/>'
        for line in LDold.errLines:
            html += line
            html += '<br/>'
        html += '</p>\n<p>Unhandled lines new dict:<br/>'
        for line in LDnew.errLines:
            html += line
            html += '<br/>'
        html += '</p>\n<p>(New) categories and category numbers:<br/>'
        html += LDnew.catDict.htmlLinkList('local')
        html += '</p>'
        hold = LDold.catDict.LDictHierarchies()
        ehwold = LDold.catDict.LDictExtraHierarchicalWords(hold)
        hnew = LDnew.catDict.LDictHierarchies()
        ehwnew = LDnew.catDict.LDictExtraHierarchicalWords(hnew)
        self.counts = {1:0,2:0,3:0,4:0,5:0}
        trhead = '<tr><td>in old cat; not in new cat<br/>in old dict; not in new dict</td><td>in old cat; not in new cat<br>in old dict; in new dict</td><td>in old cat; in new cat<br/>in old dict; in new dict</td><td>in new cat; not in old cat<br/>in old dict; in new dict</td><td>in new cat; not in old cat<br/>in new dict; not in old dict</td></tr>'
        for key in sorted(self.dictNew.keys(),key=lambda a:(int(a))):
            html += '\n<a href="#top">top</a>\n<div id="'
            html += key
            html += '">\n<p><b>Category:</b> '
            html += LDnew.catDict.getDesc(key)
            html += ' ('
            html += key
            html += ')<br/><b>matches old cat:</b> '
            if self.dictNew[key] == 'none':
                html += 'none'
            else:
                for keyOld in self.dictNew[key]:
                    html += LDold.catDict.getDesc(keyOld)
                    html += ' ('
                    html += keyOld
                    html += ') '
            html += '</p>\n<table>' + trhead + '<tr>'
            oldCatSet = set()
            self.cel={}
            if self.dictNew[key] != 'none':
                for keyOld in self.dictNew[key]:
                    oldCatSet = oldCatSet | LDold.catDict.getWords(keyOld)
                self.cel[1] = oldCatSet - LDnew.wordSet
                self.cel[2] = (oldCatSet & LDnew.wordSet) - LDnew.catDict.getWords(key)
                self.cel[3] = oldCatSet & LDnew.catDict.getWords(key)
                self.cel[4] = (LDnew.catDict.getWords(key) & LDold.wordSet) - oldCatSet
            else:
                self.cel[1] = set()
                self.cel[2] = set()
                self.cel[3] = set()
                self.cel[4] = LDnew.catDict.getWords(key) & LDold.wordSet
            self.cel[5] = LDnew.catDict.getWords(key) - LDold.wordSet
            setstar = set()
            setnostar = set()
            for w in LDnew.catDict.getWords(key) | oldCatSet:
                if w.count('*') > 0:
                    setstar.add(w)
                else:
                    setnostar.add(w)
            ehwtemp = set()
            for keyOld in self.dictNew[key]:
                if keyOld in ehwold:
                    ehwtemp = ehwtemp | ehwold[keyOld]
            for c in self.cel:
                html += '\n<td>'
                firstletter = ''
                for w in sorted(self.cel[c]):
                    if firstletter != w[0]:
                        html += '<span style="color:red;font-weight:bold">' + w[0] + ' </span>'
                    firstletter = w[0]
                    classstr = ''
                    if c < 3:
                        if (len(ehwtemp) > 0) & (w not in ehwtemp):
                            classstr = 'noehw '
                    else:
                        if key in ehwnew:
                            if w not in ehwnew[key]:
                                classstr = 'noehw '
                    match = False
                    if w.count('*') > 0:
                        pos = w.find('*')
                        for w1 in setnostar:
                            if w[:pos] == w1[:pos]:
                                match = True
                                break
                        if match == False:
                            for w1 in setstar:
                                if w != w1:
                                    pos1 = w1.find('*')
                                    pos2 = min(pos1,pos)
                                    if w[:pos2] == w1[:pos2]:
                                        match = True
                                        break
                    else:
                        for w1 in setstar:
                            pos = w1.find('*')
                            if w[:pos] == w1[:pos]:
                                match = True
                                break
                    if match == True:
                        classstr += 'match'
                    if classstr == '':
                        html += w
                    else:
                        html += '<span class="'+classstr+'">'+w+'</span>'
                    html += ' '
                html += '</td>'
            html += '</tr><tr>'
            for c in self.cel:
                html += '\n<td>'
                cellcount = len(self.cel[c])
                html += str(cellcount)
                self.counts[c] += cellcount
                html += '</td>'
            html += '</tr></table></div>'
        html += '\n<div><p><b>Totals</b><table>' + trhead + '<tr>'
        for c in sorted(self.counts):
            html += '<td>' + str(self.counts[c]) + '</td>'
        html += '</table></div>'
        html += '</body></html>'
        outFile= open(outFile,'w')
        outFile.write(html)
        outFile.close()

class LDict:
    """LIWC dictionary"""
    def __init__(self, fileName,encoding='utf-8'):
        """Reads a dictionary file if onse is provided, sets up the category dictionary object and the wordSet"""
        self.fileName = fileName
        self.errLines = []
        self.wordSet = set()
        self.catDict = LDictCatDict({})
        print('Reading dictionary file', fileName)
        if fileName == '':
            return
        dictFile= open(fileName,'r',encoding=encoding)
        print('encoding =', encoding)
        dictLine = dictFile.readline()[:-1]
        if dictLine != '%':
            print('Not a dictfile: ',dictLine)
        dictLine = dictFile.readline()[:-1]
        while dictLine != '%':
            ls = dictLine.strip().split()
            if ls[0].isdecimal():
                self.catDict.addCat(ls[0],ls[1],set())
            dictLine = dictFile.readline()[:-1]
        dictLine = dictFile.readline()[:-1]
        while (dictLine != '%') and (dictLine != ''):
            if dictLine.find('(') + dictLine.find('<') > -2:
                self.errLines.append(dictLine)
            else:
                ls = dictLine.split('\t')
#                print(dictLine)
                self.wordSet.add(ls[0])
                for j in ls[1:]:
                    self.catDict.addWord(j,ls[0])
            dictLine = dictFile.readline()[:-1]
        dictFile.close()        
        print('number of words :',len(self.wordSet))
        print('number of categories :',len(self.catDict.catDict.keys()))
    def LDictCompare(self,LDnew):
        """Compares two dictionaries"""
        print('List differences between dictionaries ',self.LDictFileName(),' and ',LDnew.LDictFileName())
        if self.errLines != LDnew.errLines:
            print('Old unhandled lines: ',self.errLines)
            print('New unhandled lines: ',LDnew.errLines)
        else:
            print('Same unhandled lines, if any')
        if self.wordSet != LDnew.wordSet:
            print('Old words not in new dict: ', len(self.wordSet - LDnew.wordSet), self.wordSet - LDnew.wordSet)
            print('New words not in old dict: ', len(LDnew.wordSet - self.wordSet), LDnew.wordSet - self.wordSet)
        else:
            print('Same words in dictionaries')
        self.catDict.catDictCompare(LDnew.catDict)
    def LDictComplete(self,LDmodel):
        """Complete a dictionary with hierarchic relationships 
        
        Takes one variable: a model dictionary.  
        The hierarchical rules derived from the model dictionary are applied to
        the existing LIWC dictionary (if in the model dictionary, all words in category 2 are also in
        category 1, the category 1 is added to each of the words in category 2
        in the existing dictionary)
        """ 
        for h in LDmodel.catDict.LDictHierarchies():
            print(h)
            self.catDict.addWordSet(h[1],self.catDict.getWords(h[0]))
    def LDictCount(self,fileList):
        """Creates a LIWC count report for a list of files"""
        cs = {self.catDict.getDesc(c) for c in self.catDict.getDictCatSet()}
        cr = LDictCountReport(cs)
        for f in fileList:
            t = LDictText(f)
            for w in t.getWords():
                cs = {self.catDict.getDesc(c) for c in self.catDict.getCatSetStarred(w.group(0).lower())}
                cr.addWord(w.group(0).lower(),cs)
        return cr
    def LDictCountString(self,string):
        """Creates LIWC counts for a string"""
        i = re.finditer(tokpatt,string,flags=re.I)
        cnt = Counter()
        for w in i:
            cnt['WC'] +=1
            for c in {self.catDict.getDesc(c) for c in self.catDict.getCatSetStarred(w.group(0).lower())}:
                cnt[c] +=1
        return cnt
    def LDictCountWordString(self,string):
        """Creates LIWC word counts for a string"""
        i = re.finditer(tokpatt,string,flags=re.I)
        liwcCountDict = {}
        wcount = Counter()
        for w in i:
            wcount[w.group(0).lower()] += 1
        for w in wcount:
            for c in {self.catDict.getDesc(c) for c in self.catDict.getCatSetStarred(w)}:
                if c not in liwcCountDict:
                    liwcCountDict[c] = Counter()
                liwcCountDict[c][w] += wcount[w]
        return liwcCountDict
    def LDictDDupAdd(self,inFile):
        """Finish deduplication of dictionary 
        
        Reintroduces deduplication file after purging of overlaps. 
        """
        errors = False
        t = ""
        addwords = set()
        print(inFile)
        f = open(inFile, newline='')
        csvReader = csv.reader(f, delimiter=';',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for row in csvReader:
            if row[0] in self.wordSet:
                errors = True
                t += row[0] + ' already in dictionary\n'
            if row[0] in addwords:
                errors = True
                t += row[0] + ' duplicate entry\n'
            addwords.add(row[0])
            for r in row[1:]:
                r2 = str(r)
                if r2 != "":
                    if ' ' in r2:
                        r2 = r2.split()[0]
                    if r2 not in self.catDict.getDictCatSet():
                        errors = True
                        t += row[0] + ' invalid category' + r +'\n'
                    else: 
                        self.catDict.addWord(r2,row[0])
        print(addwords)
        if errors:
            print(t)
            raise RuntimeError("Something bad happened")
        self.LDictComplete(self)
        return "OK"
    def LDictDDup(self,outFile):
        """Prepare deduplication of dictionary 
        
        Returns deduplication file, dictionary is stripped in the process
        Deduplication file should be manually purged of overlaps and reintroduced into stripped dictionary. 
        """
        outSet = set()
        laststar = ''
        lastprefix = 'empty'
        for w in sorted(self.wordSet):
            if w[-1] == '*':
                wshort = w[0:-1]
                if not wshort.startswith(lastprefix):
                    l = len(wshort)
                    laststar = w
                    lastprefix = wshort
                else:
                    outSet.add(laststar)
                    outSet.add(w)
                if wshort in self.wordSet:
                    outSet.add(wshort)
                    outSet.add(w)
            else:
                if (laststar != '') and (len(w) >= l) and (w[0:l] == lastprefix):
                    outSet.add(laststar)
                    outSet.add(w)
        self.wordSet = self.wordSet - outSet
        t = ''
        for w in sorted(outSet):
            t += w
            for c in sorted(self.catDict.getCatSet(w)):
                t += '\t' + str(c) + ' (' + self.catDict.getDesc(c) +')'
            t += '\n'
        outFile= open(outFile,'w')
        outFile.write(t)
        outFile.close()
        for c in self.catDict.getDictCatSet():
            self.catDict.dropWordSet(c,outSet)
        self.wordSet = self.wordSet - outSet
        return outSet
    def LDictEmptyCat(self,cat,LDmodel):
        """Removes all words from a category"""
        self.catDict.emptyCat(cat,LDmodel)
    def LDictExpand(self,wl):
        """Expands wildcard in dictionary based on wordlist"""
        for term in self.catDict.getAllWords():
            if '*' in term:
                cats = self.catDict.getCatSet(term)
                for cat in cats:
                    self.catDict.dropWord(cat,term)
                for word in [word for word in wl if word.startswith(term[:-1])]:
                    for cat in cats:
                        self.catDict.addWord(cat, word)
        self.LDictRestoreWS()
    def LDictFileName(self):
        """Returns the filename belonging to a dictionary, -none- if it is a newly created dictionary"""
        if self.fileName != '':
            return self.fileName
        else:
            return '-none-'
    def LDictCount(self,fileList):
        """Creates a LIWC count report for a list of files"""
        cs = {self.catDict.getDesc(c) for c in self.catDict.getDictCatSet()}
        cr = LDictCountReport(cs)
        for f in fileList:
            t = LDictText(f)
            for w in t.getWords():
                cs = {self.catDict.getDesc(c) for c in self.catDict.getCatSetStarred(w.group(0).lower())}
                cr.addWord(w.group(0).lower(),cs)
        return cr
    def LDictEdit(self,updfile,encoding='utf-8'):
        f = open(updfile,'r',encoding=encoding)
        lines = f.read().split('\n')
        for line in [line for line in lines if line != '']:
            l = line.split('\t')
            if l[0] == 'del':
                if l[2] == '*':
                    self.catDict.dropWordAllCats(l[1])
                elif len(l[2].split()) > 0:
                    for cat in l[2].split():
                        self.catDict.dropWord(cat,l[1])
                else: self.catDict.dropWord(l[2],l[1])
            elif l[0] == 'add':
                self.catDict.addWord(l[2],l[1])
            else:
                print(line)
                raise ValueError('Unexpected function in edit file')
        self.LDictRestoreWS()
    def LDictFreq(self,freqlist,zipout):
        """Based on a word frequency list as produced by Stylo, creates a zipfile 
        that holds csv fils holding the most frequent words in each category, once 
        with absolute and once with relative frequencies"""
        csvfile = open(freqlist,'r',newline='',encoding='iso-8859-1')
        reader = csv.reader(csvfile,delimiter='\t')
        results = {}
        relresults = {}
        for c in self.catDict.getDictCatSet():
            d = self.catDict.getDesc(c)
            results[d] = {}
            relresults[d] = {}
        firstrow = True
        for row in reader:
            if firstrow:
                firstrow = False
                files = row
                continue
            w = row[0]
            row = row[1:]
            for c in self.catDict.getCatSetStarred(w):
                d = self.catDict.getDesc(c)
                j = 0
                results[d][w] = {}
                for n in row:
                    results[d][w][files[j]] = float(n)
                    j = j + 1
        for d in results.keys():
            sums = dict.fromkeys(files,0)
            for w in results[d].keys():
                for f in results[d][w].keys():
                    sums[f] += results[d][w][f]
            rest = dict.fromkeys(files,0)
            for w in list(results[d].keys()):
                q = {k:(v/sums[k] if sums[k] > 0 else 0) for k,v in results[d][w].items()}
                if max(q.values()) < .02:
                    for k,v in results[d][w].items():
                        rest[k] += v
                    del results[d][w]
                else: 
                    relresults[d][w] = q
            if max(rest.values()) > 0:
                results[d]['rest'] = rest
        zipf = ZipFile(zipout,'w')
        kop = 'word'+';'+';'.join(files)+'\n'
        for d in results.keys():
            outfile = d + '.csv'
            txt = kop
            for w in sorted(results[d].keys()):
                txt += w
                for f in files:
                    txt += ';' + str(results[d][w][f]).replace('.',',')
                txt += '\n'
            zipf.writestr(outfile,txt)
        for d in relresults.keys():
            outfile = d + 'rel.csv'
            txt = kop
            for w in sorted(relresults[d].keys()):
                txt += w
                for f in files:
                    txt += ';' + str(relresults[d][w][f]).replace('.',',')
                txt += '\n'
            zipf.writestr(outfile,txt)
        zipf.close()
    def LDictHtml(self,outFileName,encoding='utf-8'):
        """Creates HTML representation of dictionary"""
        html = '<html>\n<head><style type="text/css">\n *{font-family: Arial,Verdana;}\
        .noehw{color:grey}</style><title>'
        html += self.fileName
        html += '</title>\n</head>\n<body>\n<a name="top"/><h1>Words in '
        html += self.fileName
        html += '</h1><p>'
        html += self.catDict.htmlLinkList('local')
        html += '</p><p>Total number of words: '
        html += str(len(self.wordSet))
        html += '</p><p>Unhandled lines:<br/>'
        for line in self.errLines:
            html += line
            html += '<br/>'
        html += '</p>'
        html += self.catDict.htmlDivList()
        html += '</body></html>'
        outFile= open(outFileName,'w',encoding=encoding)
        outFile.write(html)
        outFile.close()
    def LDictPrint(self):
        """Prints components of a dictionary"""
        print(self.fileName)
        print(self.wordSet)
        self.catDict.Lprint()
    def LDictRestoreWS(self):
        """Re-creates dictionary wordset from the categories"""
        self.wordSet = self.catDict.getAllWords()
    def LDictSubset(self,listcat):
        """Returns a new dictionary containing only selected lists categories from a given dictionary """
        LDnew = LDict('')
        for c in listcat:
            LDnew.catDict.addCat(c,self.catDict.getDesc(c),self.catDict.getWords(c))
        LDnew.LDictRestoreWS()
        return(LDnew)
    def LDictUpdate(self, fileName,LDmodel):
        """Update a LIWC Dictionary from a file
        Reads the file, creates an update report object,
        updates the dictionary and prints the report
        """
        report = LDictUpdateReport(fileName,self.fileName)
        csvReader = csv.reader(open(fileName, newline=''), delimiter=';',quotechar='"', quoting=csv.QUOTE_MINIMAL)
        firstRow = True
        for row in csvReader:
            if firstRow:
                firstRow = False
                if row[0] == 'orig':
                    updatetype = 'transfile'
                    if (row[1] != 'oldcats') | (row[2] != 'newcats') | (row[3] != 'trans') | (row[4][0:4] != 'cat:') | (row[5][0:5] != 'mode:'):
                        raise ValueError('Error in first row transfile')
                    cat = row[4][4:]
                    mode = row[5][5:]
                elif row[0] == 'cat':
                    updatetype = 'addfile'
                    if (row[1] != 'word') | (row[2][0:4] != 'cat:') | (row[3][0:5] != 'mode:'):
                        raise ValueError('Error in first row addfile')
                    cat = row[2][4:]
                    mode = row[3][5:]
                else:
                    raise ValueError('Error in first word in first row')
                report.updatetype = updatetype
                report.mode =  mode
                if cat.count(',') > 0:
                    cats = cat.split(',')
                else:
                    cats = [cat]
                report.cats =  cats
                for c in cats:
                    if mode == 'replacehierarchy':
                        self.LDictEmptyCat(c,LDmodel)
                        for h in LDmodel.catDict.LDictHierarchies():
                            if h[1] == str(c):
                                self.LDictEmptyCat(h[0],LDmodel)
                        self.LDictRestoreWS()
                    if mode == 'replace':
                        self.LDictEmptyCat(c,LDmodel)
                        self.LDictRestoreWS()
            else:
                if updatetype == 'addfile':
                    if row[1].find(' ') > -1:
                        report.addCat('splitwords')
                    else:
                        report.addCat('addition')
                        if len(row[1].split()) == 1:
                            self.catDict.addWord(row[0],mungleWord(row[1]))
                        else: report.addCat('splitwords')
                else:
                    if row[3].find('#') > -1:
                        report.addCat(row[3])
                        if row[3] == '#add':
                            for r in row[4:]:
                                if (r != ''):
                                    if (len(r.split()) == 1):
                                        for c in cats:
                                            self.catDict.addWord(c,mungleWord(r))
                                            report.addCat('addition')
                                    else: report.addCat('splitwords')
                        if row[3] == '#remove':
                            for r in row[4:]:
                                if (r != ''):
                                    if (len(r.split()) == 1):
                                        for c in cats:
                                            self.catDict.dropWord(c,mungleWord(r))
                                            report.addCat('removes')
                                    else: report.addCat('splitwords')
                    else:
                        for r in row[3:]:
                            if (r != ''):
                                if (len(r.split()) == 1):
                                    for c in cats:
                                        self.catDict.addWord(c,mungleWord(r))
                                        report.addCat('addition')
                                else: report.addCat('splitwords')
        self.LDictRestoreWS()
        report.LDictURPrint()
    def LDictWrite(self,outFile,encoding='utf-8'):
        """Very simple dictionary print"""
        if os.path.isfile(outFile):
            print(outFile,' already exists!')
            return
        outStr = '%\n'
        outStr += self.catDict.getCatLines()
        outStr += '%\n'
        outStr += self.catDict.getWordLines()
        dictFile= open(outFile,'w',encoding=encoding)
        dictFile.write(outStr)
        dictFile.close


class LDictCatDict:
    """LIWC dictionary category list"""
    def __init__(self, catDict):
        """Creates empty dictionary category list"""
        self.catDict = {}
    def addCat(self, id, desc, wordSet):
        """Adds new category with id, description and wordset into category dict"""
        self.catDict[str(int(id))]=tuple([desc,wordSet])
    def addWord(self, id, word):
        """Add word into existing category"""
        self.catDict[str(int(id))][1].add(word)
    def addWordSet(self, id, wordSet):
        """Adds set of words to existing category"""
        self.catDict[str(int(id))] = (self.getDesc(id),self.getWords(id) | wordSet)
# was         self.catDict[id]=tuple([desc,wordSet])
    def catDictCatList(self,cat,dirname):
        """Creates a list of words for a category in a given directory on disk"""
        outStr = ''
        for w in sorted(self.getWords(cat)):
            outStr = outStr + w + '\n'
        lexFile= open(dirname+self.getDesc(cat)+'.txt','w')
        lexFile.write(outStr)
        lexFile.close
    def catDictCatsList(self,dirname):
        """Creates lists of words for all categories in a given directory on disk"""
        for c in self.catDict:
            self.catDictCatList(c,dirname)
    def catDictCompare(self,newCatDict):
        """Does and prints simple category dictionary compare"""
        co = self.getDictCatSet()
        cn = newCatDict.getDictCatSet()
        if co != cn:
            print('Old categories not in new dict: (',len(co - cn),')')
            for k in co - cn:
                print (k,self.getDesc(k),len(self.getWords(k)),'words')
            print('New categories not in old dict: (',len(cn - co),')')
            for k in cn - co:
                print (k,newCatDict.getDesc(k),len(newCatDict.getWords(k)),'words')
        else:
            print('Same categories in use')
        samedescs = True
        for k in co & cn:
            if self.getDesc(k) != newCatDict.getDesc(k):
                samedescs = False
                print('Category changed description: ',k,self.getDesc(k),newCatDict.getDesc(k))
        if samedescs == True:
            print('Same categories (if any) have same descriptions')
        samewordsincats = True
        for k in co & cn:
            if self.getWords(k) != newCatDict.getWords(k):
                samewordsincats = False
                print('Category with changed words:',k,self.getDesc(k),newCatDict.getDesc(k))
                print('Removed words:',len(self.getWords(k) - newCatDict.getWords(k)), self.getWords(k) - newCatDict.getWords(k))
                print('Added words:',len(newCatDict.getWords(k) - self.getWords(k)), newCatDict.getWords(k) - self.getWords(k))
        if samewordsincats == True:
            print('Same words in corresponding categories (if any)')
    def dropCat(self,cat,LDmodel):
        """Removes a category from the dictionary and removes its words from the categories that it is included in"""
        for h in LDmodel.catDict.LDictHierarchies():
            if h[0] == str(cat):
                self.dropWordSet(h[1],self.getWords(h[0]))
        del(self.catDict[str(cat)])
    def dropWord(self, id, word):
        """Drops a word from a category"""
        self.catDict[str(int(id))][1].discard(word)
    def dropWordAllCats(self, word):
        """Drops a word from all categories"""
        for cat in self.getCatSet(word):
            self.catDict[cat][1].discard(word)
    def emptyCat(self,cat,LDmodel):
        """Empties a category from the dictionary and removes its words from the categories that it is included in"""
        for h in LDmodel.catDict.LDictHierarchies():
            if h[0] == str(cat):
                self.dropWordSet(h[1],self.getWords(h[0]))
        self.catDict[str(int(cat))] = (self.getDesc(cat),set())
    def getAllWords(self):
        """Returns all words from a dictionary"""
        ws = set()
        for c in self.catDict:
            ws = ws | self.catDict[c][1]
        return ws
    def getDesc(self, id):
        """Returns the description of a category"""
        return self.catDict[str(int(id))][0]
    def getCatDescList(self):
        """Returns a list of all category descriptions sorted by the id of the category"""
        return [self.getDesc(c) for c in sorted(self.getDictCatSet(),key=lambda a:(int(a)))]
    def getCatLines(self):
        """Returns a string of lines containing catagory id's and description, sorted by category id"""
        outStr = ""
        for c in sorted(self.catDict.keys(),key=lambda a:(int(a))):
            outStr += str(c)
            outStr += "\t"
            outStr += self.catDict[c][0]
            outStr += "\n"
        return(outStr)
    def getCats(self, word):
        """Returns a string containing all category id's of the categories that contain a word"""
        r = ''
        for c in sorted(self.getCatSet(word)):
            r += c
            r += ' '
        return r
    def getCatSet(self, word):
        """Returns a set containing all category id's of the categories that contain a word"""
        cs = set()
        for c in self.catDict:
            if word in self.catDict[c][1]:
                if c not in cs:
                    cs.add(c)
        return cs
    def getCatSetStarred(self, word):
        """Returns a set containing all category id's of the categories that would retrun a hit for the word taking into account the wildcards"""
        cs = set()
        for c in self.catDict:
            if word in self.catDict[c][1]:
                if c not in cs:
                    cs.add(c)
        if not cs:
            for i in range(len(word), 1, -1):
                for c in self.catDict:
                    if word[0:i]+'*' in self.catDict[c][1]:
                        if c not in cs:
                            cs.add(c)
                if cs:
                    break
        return cs
    def getDictCatSet(self):
        """Returns a set containing al category ids from a dictionary """
        cs = set()
        for c in self.catDict.keys():
            cs.add(c)
        return cs
    def getWordLines(self):
        """Creates string containing a line for each word in the dict, with the categories that it is included in"""
        outStr = ""
        for w in sorted(self.getAllWords(),key=str.lower):
            outStr += w
            for c in sorted(self.getCatSet(w),key=lambda a:(int(a))):
                outStr += "\t"
                outStr += str(c)
            outStr += "\n"
        return outStr
    def getWords(self, id):
        """Returns the words in a category"""
        return self.catDict[str(int(id))][1]
    def dropWordSet(self, id, wordSet):
        """Remove a set of words from a category"""
        self.catDict[str(int(id))] = (self.getDesc(id),self.getWords(id) - wordSet)
    def LDictHierarchies(self):
        """Creates a list of pairs of (included cat, including cat)"""
        l = []
        for s2 in self.catDict:
            for s1 in self.catDict:
                if (len(self.catDict[s1][1]) > 0) & (len(self.catDict[s1][1]) < len(self.catDict[s2][1])):
                    if self.catDict[s1][1] < self.catDict[s2][1]:
                        l.append((s1,s2))
        return l
    def LDictExtraHierarchicalWords(self,inclusions):
        """Creates a dictionary of extracategorical words (words not in included categories) for all categories that have included categories"""
        tl = set()
        for i in inclusions:
            if i[1] not in tl:
                tl.add(i[1])
        LDictEHW = {}
        for t in tl:
            lwl = set()
            for i in inclusions:
                if t == i[1]:
                    lwl = lwl | self.getWords(i[0])
#            print(t,self.getDesc(t))
            r = self.getWords(t)-lwl
#            print(len(r), r)
            LDictEHW[t]=r
        return LDictEHW
    def Lprint(self):
        """Prints catdict object"""
        for cat in self.catDict:
            print(cat,self.catDict[cat])
    def htmlLinkList(self,env):
        """Creates list of links to category info in dictionary print"""
        r = ''
        s = sorted(self.catDict.keys(),key=lambda a:(int(a)))
        for cat in s:
            r += '<a href="'
            if env == 'local':
                r += '#'
            r += cat
            if env != 'local':
                r += '.html'
            r += '">'
            r += self.catDict[cat][0]
            r += ' ('
            r +=  cat
            r += ')'
            r += '</a> '
        return r
    def htmlDivList(self):
        """Prints the catagories in the dictionary html print"""
        r = ''
        h = self.LDictHierarchies()
        ehw = self.LDictExtraHierarchicalWords(h)
        print(ehw)
        s = sorted(self.catDict.keys(),key=lambda a:(int(a)))
        for cat in s:
            print(cat)
            r += '\n<a href="#top">top</a>\n<div id="'
            r += cat
            r += '">\n<h2>Category '
            r += cat
            r += ', '
            r += self.catDict[cat][0]
            r += '</h2>\n<p>Number of words: '
            r += str(len(self.catDict[cat][1]))
            r += '</p>\n<p>'
            if str(cat) in ehw:
                r += '</h2>\n<p>Number of extrahierarchical words: '
                r += str(len(ehw[str(cat)]))
                r += '</p>\n<p style="font-weight:bold">Extrahierarchical words:</p>\n<p>'
                firstletter = ''
                for w in sorted(ehw[str(cat)]):
                    if w[0:1] != firstletter:
                        firstletter = w[0:1]
                        r += "<span style='color:red;font-weight:bold'>"+firstletter+"</span> "
                    r += w
                    r += ' '
                r += '</p>\n<p style="font-weight:bold">All words:</p>\n<p>'
            firstletter = ''
            for w in sorted(self.catDict[cat][1]):
                if w[0:1] != firstletter:
                    firstletter = w[0:1]
                    r += "<span style='color:red;font-weight:bold'>"+firstletter+"</span> "
                if (str(cat) not in ehw) or ((str(cat) in ehw) and (w in ehw[str(cat)])):
                    r += w
                else:
                    r += "<span class='noehw'>"+w+"</span>"
                r += ' '
            r += '</p></div>'
        return r
