import pandas as pd
pd.set_option('mode.chained_assignment', None)
import numpy as np
from scipy.linalg import block_diag
import warnings
warnings.simplefilter(action='ignore', category=UserWarning)

class MicroPrice:

    def __innit__(self):
        self.n_imbalance = None
        self.n_spread = None
        self.dt = None
        
        self.data = None
        
        self.K = None
        self.Q = None
        self.R1 = None
        self.R2 = None
        self.B = None
        self.G1 = None

    def setParams(self, imbalance, spread, delta_time, K):
        self.n_imbalance = imbalance
        self.n_spread = spread
        self.dt = delta_time
        self.K = K

    def getMicroPrice(self, data):
        self.data = data
        self.state_data = self.getStateVariables(self.data)
        self.discrete_data = self.getDiscreteData(self.state_data)
        self.symetrized_data = self.getSymetrizedData(self.discrete_data)
        self.Q, self.R1, self.q_counts = self.getQandR1(self.symetrized_data)
        self.R2 = self.getR2(self.symetrized_data, self.q_counts)
        self.G1, self.B = self.getG1andB(self.Q, self.R1, self.R2, self.K)


    def getStateVariables(self, data):
        data['Mid'] = 0.5 * (data['Bid_1'] + data['Ask_1'])
        data['Imbalance'] = data['Bid_1_Ord'] / (data['Bid_1_Ord'] + data['Ask_1_Ord'])
        data['Spread'] = (data['Ask_1'] - data['Bid_1'])
        data['Weighted_Mid'] = (data['Imbalance']*data['Ask_1']) + ((1-data['Imbalance'])*data['Bid_1'])
        return data
    
    def getDiscreteData(self, data):
        # imbalance buckets
        data['Imbalance_Bucket'] = pd.qcut(data['Imbalance'], self.n_imbalance, labels=False)
        # spread sizes
        tick_size = np.round(min(data['Spread']*100))/100
        data = data.loc[(data['Spread'] <= self.n_spread*tick_size) & data['Spread'] > 0]
        data['Spread'] = [np.round(x*100)/100 for x in data['Spread']]
        # delta mid
        data['Next_Mid'] = data['Mid'].shift(-self.dt)
        data['Next_Spread'] = data['Spread'].shift(-self.dt)
        data['Next_Time'] = data['Time'].shift(-self.dt)
        data['Next_Imbalance_Bucket'] = data['Imbalance_Bucket'].shift(-self.dt)
        data['Delta_Mid'] = np.round((data['Next_Mid'] - data['Mid'])/tick_size*2)*tick_size/2
        data = data.loc[(data['Delta_Mid'] <= tick_size*1.1) & (data['Delta_Mid'] >= -tick_size*1.1)]
        return data
    
    def getSymetrizedData(self, data):
        data_sym = data.copy(deep=True)
        data_sym['Imbalance_Bucket'] = self.n_imbalance - 1 -data_sym['Imbalance_Bucket']
        data_sym['Next_Imbalance_Bucket'] = self.n_imbalance - 1 - data_sym['Next_Imbalance_Bucket']
        data_sym['Delta_Mid'] = -data_sym['Delta_Mid']
        data_sym['Mid'] = -data_sym['Mid']
        symetrized_data = pd.concat([data, data_sym])
        symetrized_data.index = pd.RangeIndex(len(symetrized_data.index))
        return symetrized_data
    
    def getQandR1(self, data):
        no_change = data[data['Delta_Mid']==0]
        no_change_counts = no_change.pivot_table(index=['Next_Imbalance_Bucket'], columns=['Spread', 'Imbalance_Bucket'], values='Time', fill_value=0, aggfunc='count').unstack()
        q_counts = np.resize(np.array(no_change_counts[0:(self.n_imbalance*self.n_imbalance)]), (self.n_imbalance, self.n_imbalance))
        for i in range(1, self.n_spread):
            qi = np.resize(np.array(no_change_counts[(i*self.n_imbalance*self.n_imbalance):(i+1)*(self.n_imbalance*self.n_imbalance)]), (self.n_imbalance, self.n_imbalance))
            q_counts= block_diag(q_counts,qi)
        change = data[(data['Delta_Mid']!=0)]
        change_counts = change.pivot_table(index=['Delta_Mid'], columns=['Spread', 'Imbalance_Bucket'], values='Time', fill_value=0, aggfunc='count').unstack()
        r_counts = np.resize(np.array(change_counts), (self.n_imbalance*self.n_spread, 4))
        q_and_r_counts = np.concatenate((q_counts, r_counts), axis=1).astype(float)
        for i in range(0, self.n_imbalance*self.n_spread):
            q_and_r_counts[i] = q_and_r_counts[i]/q_and_r_counts[i].sum()
        Q = q_and_r_counts[:, 0:(self.n_imbalance*self.n_spread)]
        R1 = q_and_r_counts[:,(self.n_imbalance*self.n_spread):]
        return Q, R1, q_counts
    
    def getR2(self, data, q_counts):
        change = data[(data['Delta_Mid']!=0)]
        change_counts = change.pivot_table(index=['Spread', 'Imbalance_Bucket'], columns=['Next_Spread', 'Next_Imbalance_Bucket'], values='Time', fill_value=0, aggfunc='count')
        r2_counts = np.resize(np.array(change_counts), (self.n_imbalance*self.n_spread, self.n_imbalance*self.n_spread))
        q_and_r2_counts = np.concatenate((q_counts, r2_counts), axis=1).astype(float)
        for i in range(0, self.n_imbalance*self.n_spread):
            q_and_r2_counts[i] = q_and_r2_counts[i]/q_and_r2_counts[i].sum()
        R2 = q_and_r2_counts[:,(self.n_imbalance*self.n_spread):]
        return R2
    
    def getG1andB(self, Q, R1, R2, K):
        G1 = np.dot(np.dot(np.linalg.inv(np.eye(self.n_imbalance*self.n_spread)-Q),R1),K)
        B = np.dot(np.linalg.inv(np.eye(self.n_imbalance*self.n_spread)-Q),R2)
        return G1, B
