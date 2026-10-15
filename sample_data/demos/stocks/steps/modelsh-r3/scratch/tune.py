from stockkit import *
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import log_loss, accuracy_score
months=load_months(); rows=examples(months)
fit=[r for r in rows if int(r[0][:4])<2010]; test=[r for r in rows if 2010<=int(r[0][:4])<=2016]
for d in [1,2,3,4]:
 for leaf in [100,200,300,400,600,800,1200]:
  m=DecisionTreeClassifier(max_depth=d,min_samples_leaf=leaf,random_state=0).fit([r[2] for r in fit],[r[3] for r in fit])
  p=m.predict_proba([r[2] for r in test])[:,1]
  print(d,leaf,round(log_loss([r[3] for r in test],p),5),round(accuracy_score([r[3] for r in test],p>=.5),5))