import sys
sys.path.insert(0,'.')
from hoopkit import *
from sklearn.ensemble import GradientBoostingClassifier, HistGradientBoostingClassifier, AdaBoostClassifier, RandomForestClassifier, ExtraTreesClassifier
from sklearn.metrics import log_loss, accuracy_score
G=load_games(); X=featurize(G); y=[int(g['home_pts']>g['away_pts']) for g in G]
tr=[i for i,g in enumerate(G) if g['season'] in SPLITS['train']]; te=[i for i,g in enumerate(G) if g['season'] in SPLITS['dev']]
for loss in ['log_loss']:
 for n in [10,25,50,100,200]:
  for depth in [1,2,3]:
   for lr in [.01,.03,.05,.1]:
    m=GradientBoostingClassifier(n_estimators=n,max_depth=depth,learning_rate=lr,min_samples_leaf=20,loss=loss)
    m.fit([X[i] for i in tr],[y[i] for i in tr]); p=m.predict_proba([X[i] for i in te])[:,1]
    print(round(log_loss([y[i] for i in te],p),5), accuracy_score([y[i] for i in te],p>.5),n,depth,lr)
