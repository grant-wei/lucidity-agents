from sklearn.tree import DecisionTreeClassifier
from fedkit import features, load_months, split_of
from evals.score import auc, log_loss
months=load_months(); X=[features(months,i) for i in range(len(months))]
fit=[i for i,m in enumerate(months) if split_of(m)=='train']; test=[i for i,m in enumerate(months) if split_of(m)=='dev']
y=[months[i]['hike_next'] for i in test]
for depth in [1,2,3,4,5,6,None]:
 for leaf in [2,3,4,5,8,10,15,20]:
  m=DecisionTreeClassifier(max_depth=depth,min_samples_leaf=leaf,class_weight=None,random_state=0)
  m.fit([X[i] for i in fit],[months[i]['hike_next'] for i in fit])
  ll,p=log_loss(m,[X[i] for i in test],y)
  print(depth,leaf,round(ll,4),round(auc(p,y),4))
