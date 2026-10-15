from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from creditkit import features, load_customers, split_of
from evals.score import auc
import numpy as np
people=load_customers(); tr=[c for c in people if split_of(c)=='train']; te=[c for c for_dummy in []]
te=[c for c in people if split_of(c)=='dev']
X=np.array([features(c) for c in tr]); y=np.array([c['default'] for c in tr]); V=np.array([features(c) for c in te]); z=np.array([c['default'] for c in te])
for solver in ['liblinear','saga']:
 for C in [.001,.003,.01,.03,.1,.3,1,3,10,30,100]:
  m=make_pipeline(StandardScaler(),LogisticRegression(C=C,l1_ratio=1,solver=solver,max_iter=3000))
  m.fit(X,y); p=m.predict_proba(V)[:,1]
  ll=-np.mean(z*np.log(p)+(1-z)*np.log(1-p))
  print(solver,C,round(ll,6),round(auc(p,z),6))
