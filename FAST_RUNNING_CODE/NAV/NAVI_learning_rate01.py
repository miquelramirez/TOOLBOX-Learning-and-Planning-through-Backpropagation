
# coding: utf-8

# In[1]:

#NAVI_HARD_CODE_DOMAIN


# In[2]:

import matplotlib.pyplot as plt
import tensorflow as tf
import numpy as np
from sklearn.metrics import confusion_matrix
import time
from datetime import timedelta
import math
import os
import pandas as pd
#Functional coding
import functools
from functools import partial
from tensorflow.python.ops import array_ops 


# In[4]:

#Given local path, find full path
def PathFinder(path):
    #python 2
    #script_dir = os.path.dirname('__file__')
    #fullpath = os.path.join(script_dir,path)
    #python 3
    fullpath=os.path.abspath(path)
    print(fullpath)
    return fullpath

#Read Data for Deep Learning
def ReadData(path):
    fullpath=PathFinder(path)
    return pd.read_csv(fullpath, sep=',', header=0)


# In[6]:

default_settings = {
    "dims"          : 2,
    "min_maze_bound": tf.constant(0.0,dtype=tf.float32), 
    "max_maze_bound": tf.constant(10.0,dtype=tf.float32), 
    "min_act_bound": tf.constant(-0.2,dtype=tf.float32), 
    "max_act_bound": tf.constant(0.2,dtype=tf.float32), 
    "goal"    : tf.constant(8.0,dtype=tf.float32),
    "centre"  : tf.constant(5.0,dtype=tf.float32)
   }


# In[7]:

class NAVI(object):
    def __init__(self, 
                 batch_size,
                 default_settings):
        self.__dict__.update(default_settings)
        self.batch_size = batch_size
        self.zero = tf.constant(0,shape=[batch_size,2], dtype=tf.float32)
        self.two = tf.constant(2.0,dtype=tf.float32)
        self.one = tf.constant(1.0,dtype=tf.float32)
        self.lessone = tf.constant(0.99,dtype=tf.float32)
    
    def MINMAZEBOUND(self):
        return self.min_maze_bound
    
    def MAXMAZEBOUND(self):
        return self.max_maze_bound
    
    def MINACTIONBOUND(self):
        return self.min_act_bound
    
    def MAXACTIONBOUND(self):
        return self.max_act_bound
        
    def GOAL(self):
        return self.goal
    
    def CENTER(self):
        return self.centre
    
    def Transition(self, states, actions):
        previous_state = states
        distance = tf.sqrt(tf.reduce_sum(tf.square(states-self.CENTER()),1))
        scalefactor = self.two/(self.one+tf.exp(-self.two*distance))-self.lessone
        proposedLoc = previous_state + tf.matrix_transpose(scalefactor*tf.matrix_transpose(actions))
        new_states = tf.select(tf.logical_and(tf.less_equal(proposedLoc,self.MAXMAZEBOUND()),tf.greater_equal(proposedLoc,self.MINMAZEBOUND())),                               proposedLoc,                              tf.select(tf.greater(proposedLoc,self.MAXMAZEBOUND()),                                        self.zero+self.MAXMAZEBOUND(),                                        self.zero+self.MINMAZEBOUND())                              )
        return new_states
    
    def Reward(self, states,actions):
        new_reward = -tf.reduce_sum(tf.abs(states-self.GOAL()),1,keep_dims=True)
        return new_reward


# In[8]:

# States
#states = tf.placeholder(tf.float32,[1, 2],name="States")

# Actions
#actions = tf.placeholder(tf.float32,[1, 2],name="Actions")


# In[9]:

#states_list=tf.unpack(states)
#actions_list = tf.unpack(actions)
#sess = tf.InteractiveSession()
#sess.run(tf.global_variables_initializer())
#feed_dict={states:S_A_matrix[:10,2:], actions:S_A_matrix[:10,:2]}
#new_state = navi_inst._transition(1,states_list[0],actions_list[0])
#print(sess.run([new_state], feed_dict=feed_dict))
#print(sess.run([states_list[1]], feed_dict=feed_dict))
#print(sess.run([states_list[1]], feed_dict=feed_dict))


# In[10]:

#new_rewards = navi_inst.Reward(states,actions)


# In[11]:

#feed_dict={states:S_A_matrix[:10,2:], actions:S_A_matrix[:10,:2]}
#sess.run(new_rewards,feed_dict=feed_dict )


# In[12]:

class NAVICell(tf.nn.rnn_cell.RNNCell):

    def __init__(self, batch_size, default_settings):
        self._num_state_units = 2
        self._num_reward_units = 3
        self.navi = NAVI(batch_size, default_settings)

    @property
    def state_size(self):
        return self._num_state_units

    @property
    def output_size(self):
        return self._num_reward_units

    def __call__(self, inputs, state, scope=None):
        next_state =  self.navi.Transition(state, inputs)
        reward = self.navi.Reward(state, inputs)      
        return tf.concat(1,[reward,next_state]), next_state


# In[13]:

class ActionOptimizer(object):
    def __init__(self,
                a, # Actions
                num_step, # Number of RNN step, this is a fixed step RNN sequence, 12 for navigation
                num_act, # Number of actions
                batch_size, #Batch Size
                learning_rate=1): 
        self.action = tf.reshape(a,[-1,num_step,num_act]) #Reshape rewards
        print(self.action)
        self.batch_size = batch_size
        self.num_step = num_step
        self.learning_rate = learning_rate
        self._p_create_rnn_graph()
        self._p_create_loss()
        self.sess = tf.InteractiveSession()
        self.sess.run(tf.global_variables_initializer())
    
    def _p_create_rnn_graph(self):
        cell = NAVICell(self.batch_size,default_settings)
        initial_state = cell.zero_state(self.batch_size, dtype=tf.float32)
        print('action batch size:{0}'.format(array_ops.shape(self.action)[0]))
        print('Initial_state shape:{0}'.format(initial_state))
        rnn_outputs, state = tf.nn.dynamic_rnn(cell, self.action, dtype=tf.float32,initial_state=initial_state)
        #need output intermediate states as well
        concated = tf.concat(0,rnn_outputs)
        print('concated shape:{0}'.format(concated.get_shape()))
        something_unpacked =  tf.unpack(concated, axis=2)
        self.outputs = tf.reshape(something_unpacked[0],[-1,self.num_step,1])
        print(' self.outputs:{0}'.format(self.outputs.get_shape()))
        self.intern_states = tf.pack([something_unpacked[1],something_unpacked[2]], axis=2)
        self.last_state = state
        self.pred = tf.reduce_sum(self.outputs,1)
        self.average_pred = tf.reduce_mean(self.pred)
        print("self.pred:{0}".format(self.pred))
            
    def _p_create_loss(self):

        objective = tf.reduce_mean(tf.square(self.pred)) 
        self.loss = objective
        print(self.loss.get_shape())
        #self.loss = -objective
        self.optimizer = tf.train.RMSPropOptimizer(self.learning_rate).minimize(self.loss, var_list=[a])
        
    def _p_Q_loss(self):
        objective = tf.constant(0.0, shape=[self.batch_size, 1])
        for i in range(self.num_step):
            Rt = self.outputs[:,i]
            SumRj=tf.constant(0.0, shape=[self.batch_size, 1])
            #SumRk=tf.constant(0.0, shape=[self.batch_size, 1])
            if i<(self.num_step-1):
                j = i+1
                SumRj = tf.reduce_sum(self.outputs[:,j:],1)
            #if i<(self.num_step-1):
                #k= i+1
                #SumRk = tf.reduce_sum(self.outputs[:,k:],1)
            objective+=(Rt*SumRj+tf.square(Rt))*(self.num_step-i)/np.square(self.num_step)
        self.loss = tf.reduce_mean(objective)
        self.optimizer = tf.train.RMSPropOptimizer(self.learning_rate).minimize(self.loss, var_list=[a])

        
    def Optimize(self,epoch=100,show_progress=False):
#         Time_Target_List = [15,30,60,120,240,480,960]
#         Target = Time_Target_List[0]
#         counter = 0
#         new_loss = self.sess.run([self.average_pred])
#         print('Loss in epoch {0}: {1}'.format("Initial", new_loss)) 
#         print('Compile to backend complete!') 
#         start = time.time()
#         current_best = 0
#         while True:
#             training = self.sess.run([self.optimizer])
#             self.sess.run(tf.assign(a, tf.clip_by_value(a, default_settings['min_act_bound'], default_settings['max_act_bound'])))
#             end = time.time()
#             if end-start>=Target:
#                 print('Time: {0}'.format(Target))
#                 pred_list = self.sess.run(self.pred)
#                 pred_list=np.sort(pred_list.flatten())[::-1]
#                 pred_list=pred_list[:5]
#                 pred_mean = np.mean(pred_list)
#                 pred_std = np.std(pred_list)
#                 if counter == 0:
#                     current_best = pred_list[0]
#                 if pred_list[0]>current_best:
#                     current_best=pred_list[0]
#                 print('Best Cost: {0}'.format(current_best))
#                 print('MEAN: {0}, STD:{1}'.format(pred_mean,pred_std))
#                 counter = counter+1
#                 if counter == len(Time_Target_List):
#                     print("Done!")
#                     break
#                 else:
#                     Target = Time_Target_List[counter]
        
        new_loss = self.sess.run([self.loss])
        print('Loss in epoch {0}: {1}'.format("Initial", new_loss)) 
        start_time = time.time()
        for epoch in range(epoch):
            training = self.sess.run([self.optimizer])
            self.sess.run(tf.assign(a, tf.clip_by_value(a, default_settings['min_act_bound'], default_settings['max_act_bound'])))
            if True:
                new_loss = self.sess.run([self.loss])
                print('Loss in epoch {0}: {1}'.format(epoch, new_loss))  
        minimum_costs_id=self.sess.run(tf.argmax(self.pred,0))
        print(minimum_costs_id)
        best_action = np.round(self.sess.run(self.action)[minimum_costs_id[0]],4)
        print('Optimal Action Squence:{0}'.format(best_action))
        print('Best Cost: {0}'.format(self.sess.run(self.pred)[minimum_costs_id[0]]))
        pred_list = self.sess.run(self.pred)
        pred_list=np.sort(pred_list.flatten())[::-1]
        pred_list=pred_list[:5]
        pred_mean = np.mean(pred_list)
        pred_std = np.std(pred_list)
        print('Best Cost: {0}'.format(pred_list[0]))
        print('Sorted Costs:{0}'.format(pred_list))
        print('MEAN: {0}, STD:{1}'.format(pred_mean,pred_std))
        print('The last state:{0}'.format(self.sess.run(self.last_state)[minimum_costs_id[0]]))
        print('Rewards each time step:{0}'.format(self.sess.run(self.outputs)[minimum_costs_id[0]]))
        print('Intermediate states:{0}'.format(self.sess.run(self.intern_states)[minimum_costs_id[0]]))
        


# In[14]:

a = tf.Variable(tf.truncated_normal(shape=[24000],mean=0.0, stddev=0.05),name="action")
rnn_inst = ActionOptimizer(a, 120,2,100)  


# In[15]:

rnn_inst.Optimize(4000)


# In[ ]:



