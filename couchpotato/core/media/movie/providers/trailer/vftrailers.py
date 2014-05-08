# -*- coding: latin-1 -*-
import subprocess
import time
import sys
import os.path
import unicodedata
import glob
import shutil
import mechanize
import re
import urllib2
import urllib
from bs4 import BeautifulSoup
from allocine import allocine
from couchpotato.core.media.movie.providers.trailer.base import VFTrailerProvider
from couchpotato.core.helpers.variable import getTitle
from couchpotato.core.logger import CPLog
log = CPLog(__name__)

autoload = 'vftrailers'
api = allocine()
api.configure('100043982026','29d185d98c984a359e6e6f26a0474269')
rootDir = os.path.dirname(os.path.abspath(__file__))
try:
    _DEV_NULL = subprocess.DEVNULL
except AttributeError:
    _DEV_NULL = open(os.devnull, 'wb')
class vftrailers(VFTrailerProvider):
        
    def logg(self,string,debug=None):
        log.info(string)
        return True
    
    def cleantitle(self,title):
        specialchars=['(',')',',','.',';','!','?','-',':','_','[',']','|','  ','  ','  ']
        title=unicodedata.normalize('NFKD',title).encode('ascii','ignore')
        for chars in specialchars:
            title=title.replace(chars,' ')        
        return title.lower()

    def controltitle(self,title,moviename):
        realtitle=self.cleantitle(moviename[:-5].decode('unicode-escape'))
        year=moviename[len(moviename)-4:]
        listcommonwords=['youtube','dailymotion','vf','francais','francaise','vo','vost','version','annonce','bande','bande-annonce','trailer',
                         'vostfr','fr','bandeannonce','video','ba','hd','hq','720p','1080p','film','official','#1','#2',
                         '#4','#6','#7','du','and','premiere','n°1','n°2','n°3','n°4','n°5','officielle']
        wordsleft=[]
        cleantitles=self.cleantitle(title)
        for word in cleantitles.split():
            if word not in listcommonwords and word not in realtitle.split() and word<>year:
                wordsleft.append(word)
        if len(wordsleft)==0:
            return True
        else:
            return False
    def cleandic(self,dict,moviename):
        series=['2','3','4','5','6','7','8']
        titlenames=dict.keys()
        listkeysvf=[]
        listkeysvostfr=[]
        listkeysvo=[]
        year=moviename[len(moviename)-4:]
        for titledict in titlenames:
            testcontinue=self.controltitle(titledict,moviename)
            if testcontinue==False:
                continue
            cleandict=self.cleantitle(titledict)
            if not '3d' in cleandict and ('vf' in cleandict or 'francais' in cleandict or ' fr ' in cleandict) and not ' vo ' in cleandict :
                if year in cleandict:
                    listkeysvf.append(titledict)
                else:
                    compteur=0
                    for x in series:
                        if x in cleandict and not x in moviename[:-5]:
                            compteur+=1
                    if compteur==0:
                        listkeysvf.append(titledict)
            elif not '3d' in cleandict and ('vost' in cleandict):
                if year in cleandict:
                    listkeysvostfr.append(titledict)
                else:
                    compteur=0
                    for x in series:
                        if x in cleandict and not x in moviename[:-5]:
                            compteur+=1
                    if compteur==0:
                        listkeysvostfr.append(titledict)
            elif not '3d' in cleandict:
                if year in cleandict:
                    listkeysvo.append(titledict)
                else:
                    compteur=0
                    for x in series:
                        if x in cleandict and not x in moviename[:-5]:
                            compteur+=1
                    if compteur==0:
                        listkeysvo.append(titledict)
        urllistvf=[]
        urllistvostfr=[]
        urllistvo=[]
        for listkey in listkeysvf:
            urllistvf.append(dict[listkey])
        for listkey in listkeysvostfr:
            urllistvostfr.append(dict[listkey])
        for listkey in listkeysvo:
            urllistvo.append(dict[listkey])
        self.logg(str(len(urllistvf)) + ' liens de bandes annonces VF trouves sur google')
        self.logg(str(len(urllistvostfr)) + ' liens de bandes annonces VOSTFR trouves sur google')
        self.logg(str(len(urllistvo)) + ' liens de bandes annonces VO trouves sur google')
        return urllistvf,urllistvostfr,urllistvo
           
    def googlesearch(self,searchstringori):
        uploadtoignore=['UniversalMoviesFR']
        time.sleep(30)
        searchstring=searchstringori[:-5].replace(' ','+')
        urldic={}
        regexurl ="url(?!.*url).*?&amp"
        patternurl = re.compile(regexurl)
    
        regextitle='">(?!.*">).*?<\/a'
        patterntitle= re.compile(regextitle)
    
        br=mechanize.Browser()
        br.set_handle_robots(False)
        br.addheaders=[('User-agent','chrome')]
    
        query="https://www.google.fr/search?num=100&q=bande-annonce+OR+bande+OR+annonce+"+'"'+searchstring+'"'+"+VF+HD+site:http://www.youtube.com+OR+site:http://www.dailymotion.com&ie=latin-1&oe=latin-1&aq=t&rls=org.mozilla:fr:official&client=firefox-a&channel=np&source=hp&gfe_rd=cr&ei=MW9lU_vDIK2A0AXbroCADw"
        self.logg('En train de rechercher sur google : ' +searchstring)
        self.logg('Query : ' +query,True)
        htmltext=br.open(query).read()
        soup=BeautifulSoup(htmltext,"html.parser")
        search=soup.findAll('div',attrs={'id':'search'})
        searchtext = str(search[0])
        
        soup1=BeautifulSoup(searchtext,"html.parser")
        list_items=soup1.findAll('li',"html.parser")
        
        for li in list_items:
            try:
                doweignore=0
                self.logg('1'+str(li))
                soup2 = BeautifulSoup(str(li),"html.parser")
                for toignore in uploadtoignore:
                    if toignore in str(soup2):
                        doweignore+=1
                if doweignore<>0:
                    continue
                links= soup2.findAll('a')
                if not 'webcache' in str(links): 
                    self.logg('2'+str(links))
                    source_link=links[0]
                    self.logg('3'+str(source_link))
                    source_url = str(re.findall(patternurl,str(source_link))[0]).replace('url?q=','').replace('&amp','').replace('%3F','?').replace('%3D','=')
                    source_title= str(re.findall(patterntitle,str(source_link))[0]).replace('">','').replace('</a','').replace('<b>','').replace('</b>','').decode("utf-8")
                    urldic.update({source_title:source_url})
                
            except:
                continue
        self.logg(str(len(urldic))+ ' resultats trouves sur google')
        return urldic
    
    def allocinesearch(self,moviename):
        series=['2','3','4','5','6','7','8']
        listallovostfr=[]
        listallovo=[]
        listallovf=[]
        self.logg('Tentative de recherche sur Allocine de ' +moviename[:-5])
        try:
            search = api.search(moviename[:-5], "movie")
            for result in search['feed']['movie']:
                countseries=0
                ficheresult=api.movie(result['code'])
                ficheresulttitle=self.cleantitle(ficheresult['movie']['title'])
                ficheresulttitleori=self.cleantitle(ficheresult['movie']['originalTitle'])
                yearresult=ficheresult['movie']['productionYear']
                if not yearresult:
                    yearresult=0
                for x in series:
                    if (x in ficheresulttitle or x in ficheresulttitleori) and (not '3d' in ficheresulttitle and not '3d' in ficheresulttitleori):
                        if x not in moviename[:-5]:
                            countseries+=1                        
                if self.cleantitle(moviename[:-5].decode('unicode-escape')) in ficheresulttitle and countseries==0 and int(moviename[len(moviename)-4:])+2>yearresult and int(moviename[len(moviename)-4:])-2<yearresult:
                    goodresult=result
                    break
            self.logg("Resultat : Nombre [{0}] Code [{1}] Titre original [{2}]".format(search['feed']['totalResults'],
                                                                        goodresult['code'],
                                                                        goodresult['originalTitle'].encode("latin-1")))
            self.logg('Recherche de la fiche du film avec le code : ' + str(goodresult['code']))
            movieallo = ficheresult
            for x in movieallo['movie']['link']:
                if x.has_key('name') and 'Bandes annonces' in x['name']:
                    pagetrailer=x['href']
                else:
                    continue
            soup = BeautifulSoup( urllib2.urlopen(pagetrailer), "html.parser" )
            rows = soup.findAll("a")
            
            for lien in rows:
                try:
                    if 'annonce' in str(lien).lower() and 'vf' in str(lien).lower():
                        lienid=lien['href'][:lien['href'].find('&')].replace('/video/player_gen_cmedia=','')
                        self.logg("Potentiel code de bande annonce [{0}] en VF".format(lienid))
                        trailerallo = api.trailer(lienid)
                        long=len(trailerallo['media']['rendition'])
                        bestba=trailerallo['media']['rendition'][long-1]
                        linkallo=trailerallo['media']['rendition'][long-1]['href']
                        heightbaallo=bestba['height']
                        longadr=len(linkallo)
                        extallo=linkallo[longadr-3:]
                        
                        listallovf.append({'link':linkallo,'ext':extallo,'height':heightbaallo})
                        if heightbaallo>=481:
                            self.logg('Bande annonce vf et HD trouve sur Allocine jarrete de chercher')
                            break
                        else:
                            self.logg('Bande annonce vf non HD trouve sur Allocine je continue de chercher')
                    elif 'annonce' in str(lien).lower() and 'vost' in str(lien).lower():
                        lienid=lien['href'][:lien['href'].find('&')].replace('/video/player_gen_cmedia=','')
                        self.logg("Potentiel code de bande annonce [{0}] en VOSTFR".format(lienid))
                        trailerallo = api.trailer(lienid)
                        long=len(trailerallo['media']['rendition'])
                        bestba=trailerallo['media']['rendition'][long-1]
                        linkallo=trailerallo['media']['rendition'][long-1]['href']
                        heightbaallo=bestba['height']
                        longadr=len(linkallo)
                        extallo=linkallo[longadr-3:]
                        
                        listallovostfr.append({'link':linkallo,'ext':extallo,'height':heightbaallo})
                        self.logg('Bande annonce vostfr trouve sur Allocine je continue de chercher')
                    elif 'annonce' in str(lien).lower() and ' VO' in str(lien):
                        lienid=lien['href'][:lien['href'].find('&')].replace('/video/player_gen_cmedia=','') 
                        trailerallo = api.trailer(lienid)
                        long=len(trailerallo['media']['rendition'])
                        bestba=trailerallo['media']['rendition'][long-1]
                        linkallo=trailerallo['media']['rendition'][long-1]['href']
                        heightbaallo=bestba['height']
                        longadr=len(linkallo)
                        extallo=linkallo[longadr-3:]
                        if hasattr(trailerallo['media'],'subtitles') and trailerallo['media']['subtitles']['$'].lower().replace('ç','c') ==u'francais':
                            self.logg("Potentiel code de bande annonce [{0}] en VOSTFR".format(lienid))
                            listallovostfr.append({'link':linkallo,'ext':extallo,'height':heightbaallo})
                            self.logg('Bande annonce vostfr trouve sur Allocine je continue de chercher')
                        else:
                            self.logg("Potentiel code de bande annonce [{0}] en VO".format(lienid))
                            listallovo.append({'link':linkallo,'ext':extallo,'height':heightbaallo})
                            self.logg('Bande annonce vo trouve sur Allocine je continue de chercher')
                    
                    else:
                        continue
                except Exception,e:
                    print e
                    continue
            self.logg(str(len(listallovf)) +" bandes annonces en VF trouvees sur allocine")
            self.logg(str(len(listallovostfr)) +" bandes annonces en VOSTFR trouvees sur allocine")
            self.logg(str(len(listallovo)) +" bandes annonces en VO trouvees sur allocine")       
            return listallovf,listallovostfr,listallovo
        except :
            self.logg(str(len(listallovf)) +" bandes annonces en VF trouvees sur allocine")
            self.logg(str(len(listallovostfr)) +" bandes annonces en VOSTFR trouvees sur allocine")
            self.logg(str(len(listallovo)) +" bandes annonces en VO trouvees sur allocine")  
            return listallovf,listallovostfr,listallovo
    
    def quacontrol(self,url):
        quallist=[]
        p=subprocess.Popen([sys.executable, 'youtube_dl/__main__.py', '-F',url],cwd=rootDir, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        while p.poll() is None:
            l = p.stdout.readline()
            quallist.append(l)
        (out, err) = p.communicate()
        for qual in quallist:
            if 'best' in qual and ('720' in qual or '1080' in qual):
                return True
            else:
                continue
        return False
    
    def quacontrolallo(self,listallo,type):
        bestqualallo=0
        for linkvf in listallo:
            if bestqualallo<linkvf['height']:
                bestqualallo=linkvf['height']
        self.logg('Meilleure resolution trouvee sur Allocine en '+type+' : '+str(bestqualallo)+'p')
        return bestqualallo
    
    def videodl(self,cleanlist,trailername,moviename,trailerpath,allo=False,maxheight=0):
        if allo:
            for url in cleanlist:
                if maxheight==url['height']:
                    linkallo=url['link']
                    heightbaallo=url['height']
                    extallo=url['ext']
                    self.logg('Telechargement de la bande annonce suivante : ' + linkallo +' en '+str(heightbaallo)+'p en cours...')
                    try:
                        urllib.urlretrieve(linkallo, trailerpath+'.'+extallo)
                        self.logg('Une bande annonce telechargee pour ' + moviename +' sur Allocine')
                        return True
                        break
                    except:
                        continue
            return False
        else:
            bocount=0
            for bo in cleanlist:
                if bocount==0:
                    try:
                        self.logg('En train de telecharger : ' + bo + ' pour ' +moviename)
                        tempdest=unicodedata.normalize('NFKD', os.path.join(rootDir,trailername.replace("'",''))).encode('ascii','ignore')+u'.%(ext)s'
                        dest=trailerpath
                        p=subprocess.Popen([sys.executable, 'youtube_dl/__main__.py', '-o',tempdest,'--newline', '--max-filesize', '105m', '--format','best',bo],cwd=rootDir, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                        while p.poll() is None:
                            l = p.stdout.readline()
                            if 'download' in l:
                                lmsg= l.replace('%',' percent')+' '+trailername
                                self.logg(lmsg)
                        (out, err) = p.communicate()
                        self.logg(out)
                        if err:
                            self.logg(err)
                            continue
                        else:
                            listetemp=glob.glob(os.path.join(rootDir,'*'))
                            for listfile in listetemp:
                                if unicodedata.normalize('NFKD', trailername.replace("'",'')).encode('ascii','ignore') in listfile:
                                    ext=listfile[-4:]
                                    destination=dest+ext
                                    shutil.move(listfile, destination)
                                    bocount=1
                                    self.logg('Une bande annonce telechargee pour ' + moviename)
                                    return True
                    except:
                        continue
                else:
                    continue
            return False
    
    def totqualcontrol(self,listcontrol,type):
        compteurhd=0
        cleanlist=[]
        listlowq=[]
        for tocontrolqual in listcontrol:
            if compteurhd==3:
                self.logg('Suffisamment de bandes annonces '+type+ ' HD trouvees plus la peine de continuer')
                break
            self.logg('Controle de la qualite reelle de ' +tocontrolqual+ ' en cours...')
            
            if self.quacontrol(tocontrolqual):
                self.logg('La qualite de ' +tocontrolqual+' semble HD je rajoute a la liste  HD '+type)
                cleanlist.append(tocontrolqual)
                compteurhd+=1
            else:
                self.logg('Pfffff encore un mytho la qualite de ' +tocontrolqual+' nest pas HD je rajoute a la liste non HD '+type)
                listlowq.append(tocontrolqual)
        return cleanlist, listlowq
    
    def search(self, group, filename, destination):
        movie_name = getTitle(group)
        movienorm = unicodedata.normalize('NFKD', movie_name).encode('ascii','ignore')
        movie_year = group['media']['info']['year']
        moviename=movienorm+' '+ str(movie_year)
        listvfallo,listvostfrallo,listvoallo=self.allocinesearch(moviename)
        if listvfallo:
            maxqual=self.quacontrolallo(listvfallo,'vf')
            
            if maxqual>=481:
                self.videodl(listvfallo,filename,moviename,destination,True,maxqual)
                return True
            else:
                self.logg('Bande annonce en VF non HD trouvee sur Allocine tentative de recherche dune meilleure qualite sur google')
        else:
            self.logg('Rien trouve sur Allocine en VF tentative de recherche sur google')
        urldic=self.googlesearch(moviename)
        listgooglevf, listgooglevostfr,listgooglevo=self.cleandic(urldic,moviename)
        if listvfallo:
            maxqual=self.quacontrolallo(listvfallo,'vf')
            if listgooglevf:
                self.logg('Jai trouve des bandes annonces VF sur google, controlons leur qualite')
                cleanlistvf,listlowqvf=self.totqualcontrol(listgooglevf,'vf')
                if cleanlistvf:
                    self.logg('Si jen crois google jai trouve mieux que la bande annonce allocine . Lets go')
                    self.videodl(cleanlistvf,filename,moviename,destination)
                    return True
                else:
                    self.logg('Rien trouve de mieux sur google pour : '+moviename+' je telecharge donc la bande annonce non HD vf Allocine')
                    maxqual=self.quacontrolallo(listvfallo,'vf')
                    self.videodl(listvfallo,filename,moviename,destination,True,maxqual)
                    return True
            else:
                self.logg('Rien trouve de mieux sur google pour : '+moviename+' je telecharge donc la bande annonce non HD vf Allocine')
                maxqual=self.quacontrolallo(listvfallo,'vf')
                self.videodl(listvfallo,filename,moviename,destination,True,maxqual)
                return True
            
        elif listgooglevf:
            cleanlistvf,listlowqvf=self.totqualcontrol(listgooglevf,'vf')
            if cleanlistvf:
                self.logg('Si jen crois google jai trouve mieux que la bande annonce allocine . Lets go')
                self.videodl(cleanlistvf,filename,moviename,destination)
                return True
            elif listlowqvf:
                self.logg('Rien trouve sur Allocine pour : ' +moviename+' je recupere donc une bande annonce non HD vf trouve sur google')
                self.videodl(listlowqvf,filename,moviename,destination)
                return True
        elif listvostfrallo:
            maxqual=self.quacontrolallo(listvostfrallo,'vostfr')
            if maxqual>=481:
                self.videodl(cleanlistvf,filename,moviename,destination,True,maxqual)
                return True
            else:
                if listgooglevostfr:
                    cleanlistvostfr,listlowqvostfr=self.totqualcontrol(listgooglevostfr,'vostfr')
                    if cleanlistvostfr:
                        self.logg('Si jen crois google jai trouve mieux que la bande annonce allocine . Lets go')
                        self.videodl(cleanlistvostfr,filename,moviename,destination)
                        return True    
                    else: 
                        self.logg('Rien trouve de mieux sur google pour : '+moviename+' je telecharge donc la bande annonce non HD vostfr Allocine')
                        self.videodl(listvostfrallo,filename,moviename,destination,True,maxqual)
                        return True
                else: 
                    self.logg('Rien trouve de mieux sur google pour : '+moviename+' je telecharge donc la bande annonce non HD vostfr Allocine')
                    self.videodl(listvostfrallo,filename,moviename,destination,True,maxqual)
                    return True
        
        elif listgooglevostfr:
            cleanlistvostfr,listlowqvostfr=self.totqualcontrol(listgooglevostfr,'vostfr')
            if cleanlistvostfr:
                self.logg('Si jen crois google jai trouve mieux que la bande annonce allocine . Lets go')
                self.videodl(cleanlistvostfr,filename,moviename,destination)
                return True
            elif listlowqvostfr:
                self.logg('Rien trouve sur Allocine pour : ' +moviename+' je recupere donc une bande annonce non HD vostfr trouve sur google')
                self.videodl(listlowqvostfr,filename,moviename,destination)
                return True
        elif listvoallo:
            maxqual=self.quacontrolallo(listvoallo,'vo')
            if maxqual>=481:
                self.videodl(listvoallo,filename,moviename,destination,True,maxqual)
                return True
            else:
                if listgooglevo:
                    cleanlistvo,listlowqvo=self.totqualcontrol(listgooglevo,'vo')
                    if cleanlistvo:
                        self.logg('Si jen crois google jai trouve mieux que la bande annonce allocine . Lets go')
                        self.videodl(cleanlistvo,filename,moviename,destination)
                        return True    
                    else: 
                        self.logg('Rien trouve de mieux sur google pour : '+moviename+' je telecharge donc la bande annonce non HD vo Allocine')
                        self.videodl(listvoallo,filename,moviename,destination,True,maxqual)
                        return True
                else: 
                    self.logg('Rien trouve de mieux sur google pour : '+moviename+' je telecharge donc la bande annonce non HD vo Allocine')
                    self.videodl(listvoallo,filename,moviename,destination,True,maxqual)
                    return True
                
        elif listgooglevo:
            cleanlistvo,listlowqvo=self.totqualcontrol(listgooglevo,'vos')
            if cleanlistvo:
                self.logg('Si jen crois google jai trouve mieux que la bande annonce allocine . Lets go')
                self.videodl(cleanlistvo,filename,moviename,destination)
                return True
            elif listlowqvo:
                self.logg('Rien trouve sur Allocine pour : ' +moviename+' je recupere donc une bande annonce non HD vo trouve sur google')
                self.videodl(listlowqvo,filename,moviename,destination)
                return True
        else:
            self.logg('Snifff encore un film pourri pas de bande annonce trouve pour ' + moviename)
            return False
