from sklearn.ensemble import GradientBoostingClassifier
from fedkit import load_months, features, split_of
from evals.score import log_loss, auc
m=load_months(); tr=[i for i,x in enumerate(m) if split_of(x)=='train']; dv=[i for i,x in enumerate(m) if split_of(x)=='dev']; X=[features(m,i) for i in range(len(m))]; y=[m[i]['hike_next'] for i in dv]
out=[]
for n in [5,10,15,20,30,40,60,80,120]:
 for d in [1,2,3]:
  for lr in [.01,.02,.03,.05,.1]:
   for leaf in [3,8,15]:
    model=GradientBoostingClassifier(n_estimators=n,max_depth=d,learning_rate=lr,min_samples_leaf=leaf,subsample=.8,random_state=0)
    model.fit([X[i] for i in tr],[m[i]['hike_next'] for i in tr]); ll,p=log_loss(model,[X[i] for i in dv],y); out.append((ll,auc(p,y),n,d,lr,leaf))
print(*sorted(out)[:20],sep='\n')
