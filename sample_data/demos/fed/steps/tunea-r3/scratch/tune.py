from itertools import combinations
from fedkit import *
from sklearn.linear_model import LinearRegression
import numpy as np
from evals.score import log_loss, auc
m=load_months(); X=np.array([features(m,i) for i in range(len(m))]);
tr=[i for i,x in enumerate(m) if split_of(x)=='train']; dv=[i for i,x in enumerate(m) if split_of(x)=='dev']; y=np.array([x['hike_next'] for x in m]);
for n in range(1,9):
 for cols in combinations(range(8),n):
  model=LinearRegression().fit(X[tr][:,cols],y[tr]); p=np.clip(model.predict(X[dv][:,cols]),.01,.99)
  ll,_=log_loss(type('M',(),{'predict_proba':lambda s,z:np.column_stack([1-np.clip(model.predict(np.array(z)[:,cols]),.01,.99),np.clip(model.predict(np.array(z)[:,cols]),.01,.99)])})(),X[dv],y[dv])
  if ll<.25: print(round(ll,4),cols,round(auc(p,y[dv]),4))
