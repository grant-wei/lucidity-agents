import sys
sys.path.insert(0,'.')
from fedkit import load_months, features, split_of
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.metrics import log_loss, roc_auc_score
m=load_months(); X=[features(m,i) for i in range(len(m))]
tr=[i for i,x in enumerate(m) if split_of(x)=='train']; dv=[i for i,x in enumerate(m) if split_of(x)=='dev']
y=[m[i]['hike_next'] for i in dv]
for leaf in [2,3,4,5,8,10,15,20,30,40,60]:
 for weight in [None,'balanced','balanced_subsample']:
  model=RandomForestClassifier(n_estimators=300,min_samples_leaf=leaf,class_weight=weight,max_features=1.0,random_state=42,n_jobs=-1)
  model.fit([X[i] for i in tr],[m[i]['hike_next'] for i in tr]); p=model.predict_proba([X[i] for i in dv])[:,1]
  print(leaf,weight,round(log_loss(y,p),5),round(roc_auc_score(y,p),5))
