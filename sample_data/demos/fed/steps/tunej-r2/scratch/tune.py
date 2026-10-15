from sklearn.ensemble import GradientBoostingClassifier, HistGradientBoostingClassifier, RandomForestClassifier, ExtraTreesClassifier, AdaBoostClassifier
from fedkit import load_months, features, split_of
from evals.score import log_loss, auc
m=load_months(); X=[features(m,i) for i in range(len(m))]
tr=[i for i,x in enumerate(m) if split_of(x)=='train']; dv=[i for i,x in enumerate(m) if split_of(x)=='dev']; y=[m[i]['hike_next'] for i in dv]
models=[]
for n in [10,20,30,50,75,100]:
 for d in [1,2,3]:
  for lr in [.02,.05,.1]:
   models.append(GradientBoostingClassifier(n_estimators=n,max_depth=d,learning_rate=lr,min_samples_leaf=3, random_state=0))
for leaf in [5,10,15,20,30]:
 for l2 in [0,1,10]: models.append(HistGradientBoostingClassifier(max_iter=100, max_leaf_nodes=leaf, l2_regularization=l2, learning_rate=.05, random_state=0))
for mod in models:
 mod.fit([X[i] for i in tr],[m[i]['hike_next'] for i in tr]); ll,p=log_loss(mod,[X[i] for i in dv],y)
 print(round(ll,5),round(auc(p,y),5),mod.get_params())