import re

data = open('rawChat.txt',"r")
toy = open('train.txt','w')
toy2= open('dev.txt','w')
i = 0
for line in data:
    i+=1
    print i
    if i<15000000:
    	fixed = re.sub('\[.+?(?=\])\]','',line)	
    	fixed = re.sub('.+?(?=\:)\: ','',fixed,1)
    	toy.write(fixed)
    elif i<16000000:
    	fixed = re.sub('\[.+?(?=\])\]','',line)
    	fixed = re.sub('.+?(?=\:)\: ','',fixed,1)
    	toy2.write(fixed)
    if i>16000000:
	break
