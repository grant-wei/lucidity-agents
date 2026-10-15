import math
from hoopkit import *
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
G=load_games(); X=featurize(G); y=[int(g['home_pts']>g['away_pts']) for g in G]
fit=[i for i,g in enumerate(G) if g['season'] in SPLITS['train']]; test=[i for i,g in enumerate(G) if g['season'] in SPLITS['dev']]
for kernel in ['rbf','linear']:
 for C in [.01,.03,.1,.3,1,3,10]:
  for gamma in (['scale'] if kernel=='linear' else ['scale',.01,.1]):
   m=make_pipeline(StandardScaler(),SVC(C=C,kernel=kernel,gamma=gamma,probability=True,random_state=0))
   m.fit([X[i] for i in fit],[y[i] for i in fit]); p=m.predict_proba([X[i] for i in test])[:,1]
   ll=-sum(math.log(max(1e-6,min(1-1e-6,q)) if y[i] else max(1e-6,min(1-1e-6,1-q)) for q,i in zip(p,test))/len(test)
   acc=sum((q>.5)==bool(y[i]) for q,i in zip(p,test))/len(test)
   print(kernel,C,gamma,round(ll,5),round(acc,4),flush=True)
