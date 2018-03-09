import os
import sys
import datetime
import pandas as pd
from sklearn.metrics.classification import accuracy_score, log_loss
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import StratifiedKFold

src_dir = os.path.join(os.getcwd(), 'src')
sys.path.append(src_dir)

from data.data import Data, DataConcat


class processing:
    
    def __init__(self, countries=['A', 'B', 'C'], 
                 balances={'A':False, 'B':False, 'C':False}):
        self.countries = countries
        self.balances = balances
        self.exclude_dict = {'A': [], 'B': [],'C': []}
        self.data_dict = None
        self.model_dict = None
        self.vote_waights_dict = None
    
    def set_vote_waights_dict(self, vote_waights_dict):
        self.vote_waights_dict = vote_waights_dict

    def set_data_dict(self, data_dict):
        self.data_dict = data_dict
        
    def set_model_dict(self, model_dict):
        self.model_dict = model_dict
    
    def set_exclude_dict(self, exclude_dict):
        self.exclude_dict = exclude_dict
        
    def save_csv(self, df, clf_model_name = '_', path=''):
        submission_file = os.path.join(path + 'submission_'+ clf_model_name + '_' +
                                       str(datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")) + '.csv')
        print('submission file:', submission_file)
        df.to_csv(submission_file, index=True, float_format='%.4f')
        print(df.head())

 
    def find_exclude(self, splits=5):
        if not self.model_dict or not self.data_dict or not self.filenames_dict:
            print('Stoped: no models or data')
            return None
        
        for c in self.countries:
            #self.data_dict[c].set_country(c)
            #self.data_dict[c].load(load=True)    
            self.model_dict[c].load_data(data=self.data_dict[c], balance=self.balances[c])
            exclude_list = []
            finish = False
            logloss_dict = {}
            while not finish:
                self.model_dict[c].set_exclude_list(exclude_list)
                clf = self.model_dict[c].train()
                exclude_list_prev = exclude_list.copy()
                columns = [x for x in self.model_dict[c].get_train().columns if x not in exclude_list_prev]
                exclude_list = [x  for (x,y) in zip(columns, 
                                                    self.model_dict[c].get_feature_importances()) if y == 0]
                if not exclude_list:
                    finish = True  
                exclude_list = exclude_list_prev + exclude_list

                logloss_iter = []
                splits = self.model_dict[c].data.get_train_valid(n_splits=splits, balance=self.balances[c])

                for i in range(0, splits):
                    self.model_dict[c].set_random_seed(i)
                    train, valid = splits[i]
                    self.model_dict[c].set_exclude_list(exclude_list)
                    self.model_dict[c].train(train[0], train[1])
                    pred = self.model_dict[c].predict(valid[0])
                    logloss_iter.append(log_loss(valid[1].astype(int), pred['poor']))
                logloss = np.mean(logloss_iter)
                logloss_dict[logloss] = exclude_list
                print('loglos: {0} exclude length: {1}'.format(logloss, len(exclude_list)))
            self.exclude_dict[c] = logloss_dict[np.min(list(logloss_dict.keys()))]
            print('Country: {0} exclude length: {1}'.format(c, len(self.exclude_dict.get(c))))

        return logloss_dict
    
    def predict(self, model_name, path=''):
        if not self.model_dict or not self.data_dict:
            print('Stoped: no models or data')
            return None
        
        predictions = []
        for c in self.countries:
            #self.data_dict[c].set_country(c)
            #self.data_dict[c].load(load=True) 
            self.model_dict[c].load_data(data=self.data_dict[c], balance=self.balances[c])
            self.model_dict[c].set_exclude_list(self.exclude_dict[c])
            if self.vote_waights_dict:
                self.model_dict[c].set_weights(self.vote_waights_dict[c])
            print('exclude: \n', self.exclude_dict[c])
            self.model_dict[c].train()
            predictions.append(self.model_dict[c].predict())
        result = pd.concat(predictions)    
        self.save_csv(result, clf_model_name=model_name, path=path)
        return result
  