import numpy as np
from sklearn.naive_bayes import GaussianNB
from hoopkit import *
from sklearn.metrics import log_loss, accuracy_score
G=load_games(); X=np.array(featurize(G)); y=np.array([int(g['home_pts']>g['away_pts']) for g in G]); ix=[i for i,g in enumerate(G) if g['season']<=2012]; iv=[i for i,g in enumerate(G) if g['season']==2013]
forms={'rate':(X[:,0]-X[:,1])[:,None], 'elo':X[:,2,None], 'both':np.column_stack([X[:,0]-X[:,1],X[:,2]]), 'sum':((X[:,0]-X[:,1])+X[:,2])[:,None]}
for name,z in forms.items():
 for smooth in [1e-9,.001,.01,.05,.1,.5,1,2]:
  m=GaussianNB(var_smoothing=smooth).fit(z[ix],y[ix]); p=m.predict_proba(z[iv])[:,1]
  print(name,smooth,round(log_loss(y[iv],p),5),round(accuracy_score(y[iv],p>.5),5))
