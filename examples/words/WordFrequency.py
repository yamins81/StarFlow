from System.Utils import MakeDir,Contents,is_external_url
import os
import numpy as np
import tabular as tb
from BeautifulSoup import BeautifulSoup

root = '../Words/'
root_wf = '../Words/WordFrequencyData/'

def Initialize(creates = root):
	MakeDir(root)

def Initialize_wf(creates = root_wf):
	MakeDir(root_wf)

def GetFiles(depends_on = 'http://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/',creates = (root_wf + '1To10000.html',root_wf + '10001To20000.html',root_wf + '20001To30000.html',root_wf + '30001To40000.html')):
	for (s,e) in [(1,10000),(10001,20000),(20001,30000),(30001,40000)]:
		os.system('wget http://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/PG/2006/04/' + str(s) + '-' + str(e) + ' -O ' + root_wf + str(s) + 'To' + str(e) + '.html')
		
def ParseFiles(depends_on =  (root_wf + '1To10000.html',root_wf + '10001To20000.html',root_wf + '20001To30000.html',root_wf + '30001To40000.html'), creates = root_wf + 'WordFrequencies.csv'):

	Words = []
	Freqs = []
	Rank = []
	for (j,x) in enumerate(depends_on):
		Soup = BeautifulSoup(open(x,'r'))
		P = Soup.findAll('p')
		count = 0
		for (i,p) in enumerate(P):
			print 'processing', x, ', group', i
			A = p.findAll('a')
			if len(A) > 10:
				C = Contents(p).replace(' = ',' ').split(' ')
				newwords = C[::2] ; newfreqs = C[1::2]
				Words += newwords
				Freqs += newfreqs
				Rank += range(1+j*10000 + count,1+j*10000 + count + len(newwords))
				count += len(newwords)
				

	tb.tabarray(columns = [Words,Freqs,Rank],names=['Word','Frequency','Rank']).saveSV(creates,delimiter = ',')
	
def PageWordFreqs(page):
	if is_external_url(page):
		os.system('wget ' + page + ' -O test.html')
		file = 'test.html'
	else:
		file = page
	
	try:
		Soup = BeautifulSoup(open(file,'r'))
	except:
		pass
	else:
		C = Contents(Soup).replace('\n',' ')
		CW = [x for x in C.lower().split(' ') if x.isalpha()]
		Carray = tb.tabarray(columns = [CW,range(len(CW))],names=['Word','Frequency'])
	
		CAgg = Carray.aggregate(On=['Word'],AggFunc=lambda x : len(x))
	
		return CAgg
	
	
def HiAssocWords(page,depends_on = root_wf + 'WordFrequencies.csv'):

	CFreq = PageWordFreqs(page) 
	
	if CFreq != None:
	
		WFreq = tb.tabarray(SVfile = depends_on,verbosity=0) 
	
		WF = WFreq[tb.fast.isin(WFreq['Word'],CFreq['Word'],)]
		
		CC = CFreq.join(WF,keycols='Word',Names=['InPage','Overall'])
	
		N = float(CFreq['Frequency'].sum())
		
		DD = (1/N) * CC['Frequency_InPage']  -  10**(-9) * CC['Frequency_Overall']
		s = DD.argsort()[::-1]
		DD = DD[s]
		CC = CC[s]
		CC = CC.addcols(DD,names='FrequencyDelta')
			
		return CC[['Word','Frequency_InPage','FrequencyDelta']]
	
	else:
		return None