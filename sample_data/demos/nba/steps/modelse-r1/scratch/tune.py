import math
from hoopkit import SPLITS, featurize, load_games
from sklearn.linear_model import LogisticRegression

games=load_games(); X=featurize(games); y=[int(g['home_pts']>g['away_pts']) for g in games]
tr=[i for i,g in enumerate(games) if g['season'] in SPLITS['train']]
te=[i for i,g in enumerate(games) if g['season'] in SPLITS['dev']]
for c in [.001,.003,.01,.03,.1,.3,1,3,10,30,100,300,1000]:
 m=LogisticRegression(C=c,solver='lbfgs',max_iter=1000).fit([X[i] for i in tr],[y[i] for i in tr])
 p=m.predict_proba([X[i] for i in te])[:,1]
 ll=-sum(math.log(q if y[i] else 1-q) for q,i in zip(p,te))/len(te)
 acc=sum((q>.5)==bool(y[i]) for q,i in zip(p,te))/len(te)
 print(c,round(ll,6),round(acc,5))
