import math
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from fedkit import features, load_months, split_of
months=load_months(); train=[i for i,m in enumerate(months) if split_of(m)=='train']; dev=[i for i,m in enumerate(months) if split_of(m)=='dev']
X=[[features(months,i)[j] for j in range(8)] for i in train+dev]; y=[months[i]['hike_next'] for i in train+dev]; n=len(train)
for k in [3,5,7,9,11,15,21,31,41,61,81]:
 for w in ['uniform','distance']:
  for p in [1,2]:
   model=make_pipeline(StandardScaler(),KNeighborsClassifier(n_neighbors=k,weights=w,p=p)); model.fit(X[:n],y[:n]); probs=model.predict_proba(X[n:])[:,1]; yt=y[n:]
   ll=-sum(math.log(max(1e-6,min(1-1e-6,q)) if t else 1-max(1e-6,min(1-1e-6,q)) for q,t in zip(probs,yt))/len(yt)
   print(round(ll,5),k,w,p)
